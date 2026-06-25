# Architecture Deep Dive

This document explains *why* the system is built around Kafka instead of
direct service-to-service calls, breaks down exactly what each service
produces and consumes, walks through the full event flow for a single
order, and covers error handling and data-consistency trade-offs as they
actually exist in the code today (including the parts that are
half-implemented).

---

## 1. Why Event-Driven

The order workflow has a shape that maps naturally onto pub/sub rather than
request/response:

- **Multiple independent reactions to one fact.** When an order is placed
  (`Order-placed`), both the Restaurant Manager (to confirm with the
  restaurant) and the Delivery Route Service (to start tracking the route)
  need to react. Neither needs to know the other exists. With direct HTTP
  calls, the Order Service would need to know about, call, and handle
  failures for every downstream consumer. With Kafka, it just publishes
  once.
- **Long-running, asynchronous steps in the middle of a "request."**
  Whether a restaurant accepts an order isn't instantaneous — in this
  codebase it's simulated with a 10-second wait, but in reality it could be
  minutes. Modeling that as a blocking HTTP call from the customer's
  request would tie up a connection for the whole wait. Modeling it as
  "publish `order-created`, react later with `res-available`" lets the
  HTTP request to `/Order` return immediately while the workflow continues
  in the background, with status pushed to the customer over a WebSocket
  as it progresses.
- **Loose coupling for independent deployability.** The Order Service, the
  Restaurant Manager, and the Delivery Route Service are deployed as three
  separate containers with no shared code and no direct network dependency
  on each other's internals — only a shared Kafka broker and (in one place)
  one synchronous HTTP lookup.
- **Natural extension point.** Adding a new consumer (e.g. a notifications
  service, an analytics pipeline) only requires subscribing to existing
  topics — no changes to producers.

The trade-off, covered honestly in §4 below, is that this buys flexibility
at the cost of consistency guarantees: this is a **choreography**-style
saga (each service reacts independently to events) rather than an
**orchestration**-style one (a central coordinator drives the whole
workflow), and the codebase doesn't yet have compensating transactions,
idempotency keys, or a dead-letter strategy to fully back that up.

---

## 2. Producer / Consumer Breakdown Per Service

### Order Service (`OrderManager`)
- **Produces:**
  - `order-created` — on `POST /Order`, once the cart is parsed and
    restaurant/customer locations are resolved.
  - `Order-placed` — from `Handler/res_available.py`, once the per-order
    event counter reaches 2 (i.e. the aggregation condition is met).
- **Consumes:**
  - `res-available` — increments the order's event counter; if it's the
    `2nd` signal, triggers `Order-placed` and an `Order-placed`
    confirmation to the customer's WebSocket.
  - `Del-available` — same aggregation logic, intended to come from a
    delivery-partner-matching service not present in this codebase (see
    README §4 for the caveat).
- **Group ID:** `orderapi-group`.

### Restaurant Manager (`ResManager`)
- **Produces:**
  - `res-available` — from `Handlers/Ordercreated.py`, after pushing the
    order to restaurant WebSocket(s) and waiting to see if they all
    accepted.
- **Consumes:**
  - `order-created` — triggers the restaurant push + accept-wait flow.
  - `Order-placed` — triggers a final "confirmed" push to restaurant
    WebSocket(s).
- **Group ID:** `resmanager-group-test`.

### Delivery Route Service (`delivery_route_service`)
- **Produces:** none. This service is consumer-only in the current
  implementation — it never publishes back onto Kafka, it only serves HTTP
  reads (`/getLocation`, `/map`, `/status`) once it has cached an order's
  location data.
- **Consumes:**
  - `Order-placed` — caches `order_info` (restaurant, delivery, and
    customer coordinates) into an in-memory dict keyed by order ID.
- **Group ID:** `route-service-group`.

### Summary Table

| Service | Produces | Consumes |
|---|---|---|
| Order Service | `order-created`, `Order-placed` | `res-available`, `Del-available` |
| Restaurant Manager | `res-available` | `order-created`, `Order-placed` |
| Delivery Route Service | *(none)* | `Order-placed` |

---

## 3. Event Flow Narrative: What Happens When a User Places an Order

1. The customer's browser POSTs a cart to `Order Service: POST /Order`.
2. The Order Service synchronously calls `Restaurant Manager: GET
   /api/ResManager/res/restaurants/{id}` for each distinct restaurant in
   the cart, to get current lat/long. (This is the one deliberate
   synchronous coupling in the system — it's a quick lookup, not part of
   the saga, so it's done inline rather than via an event.)
3. The Order Service assigns a random `order_id`, stores order state
   (`res_locations`, `order_location`) in its in-memory `order_status`
   dict, and returns `{"Status": "Requested"}` to the HTTP caller
   immediately.
4. In the background, the Order Service publishes `order-created` to
   Kafka and returns control to the event loop — the HTTP response has
   already gone out by this point.
5. The Restaurant Manager's consumer picks up `order-created` on group
   `resmanager-group-test`. For each restaurant in the cart, it pushes the
   order detail down that restaurant's open WebSocket connection
   (`/communicate/ws`), and marks the order `"Requested"` in its own
   in-memory restaurant registry.
6. The Restaurant Manager waits (currently `asyncio.sleep(10)` — a
   stand-in for "give the restaurant time to respond") and then checks
   whether every restaurant in the cart has flipped its `OrderStatus` for
   this order to `"accepted"` (set via messages the restaurant dashboard
   sends back over the same WebSocket).
7. The Restaurant Manager publishes `res-available` with a `flag`
   indicating whether the whole order was accepted.
8. The Order Service's consumer picks up `res-available` on group
   `orderapi-group`. It increments a per-order counter
   (`Event_counter[oid]`). The handler is written to wait for **two**
   signals before proceeding — in the intended design this second signal
   is `Del-available` from a delivery-partner-matching service. Since that
   producer doesn't exist in this codebase, in practice the counter only
   reaches 2 if both `res-available` and `Del-available` happen to be
   delivered for the same order — which won't currently happen without an
   external producer for `Del-available`.
9. Once the aggregation condition is satisfied, the Order Service publishes
   `Order-placed`, carrying the full `order_info` bundle (restaurant
   locations, customer location, and — if available — delivery location),
   and pushes a `{"oid": ..., "flag": ...}` status update to the customer
   over `WS /ws`.
10. Two consumers react to `Order-placed` independently and in parallel:
    - The **Restaurant Manager** sends a final "Confirmed the order!!!"
      push to each restaurant's WebSocket.
    - The **Delivery Route Service** stores `order_info` in its own
      in-memory `order_status` dict, keyed by `str(order_id)`.
11. The customer (or the frontend on their behalf) can now poll
    `Delivery Route Service: GET /map/{order_id}`, which fetches two
    routes from OpenRouteService in parallel (delivery→restaurant,
    restaurant→customer) and serves a Leaflet map rendering both legs plus
    markers for all three points.

---

## 4. Error Handling and Retry Strategy

**Consumer-side resilience.** Every consumer (`Consumer.py` in
OrderManager and ResManager, `consumer.py` in the Delivery Route Service)
follows the same pattern:

```python
while True:
    try:
        consumer = AIOKafkaConsumer(...)
        await consumer.start()
        async for msg in consumer:
            asyncio.create_task(handle_event(event))  # non-blocking
    except Exception as e:
        await asyncio.sleep(3)   # back off and reconnect
    finally:
        await consumer.stop()
```

This protects against the broker being temporarily unreachable (e.g. at
startup, before Kafka has finished initializing) by reconnecting every 3
seconds indefinitely. It does **not** protect against errors *within* an
individual message handler — each message is dispatched into its own
`asyncio.create_task`, so an exception inside a handler is swallowed by
that task and doesn't crash the consumer loop, but it also isn't logged
anywhere centrally, retried, or routed to a dead-letter topic.

**Producer-side error handling.** Every `producer.send(...)` call is
wrapped in a `try/except` that logs the exception and otherwise does
nothing — there's no retry-with-backoff, no outbox pattern, and no
guarantee the event is ever successfully published if the first attempt
fails. A failed `order-created` publish, for instance, would leave the
customer's order in `"Requested"` state in memory forever, with no signal
to the customer that anything went wrong (today's `/Order` handler
already returns the HTTP success response *before* knowing whether the
publish succeeded).

**Offset commit semantics.** All consumers use `enable_auto_commit=True`,
which commits offsets on a timer rather than after successful processing.
Combined with `auto_offset_reset="latest"` (new consumer groups start from
the newest offset, not the oldest), this means:
- A consumer that crashes mid-processing can lose in-flight events rather
  than reprocessing them (no at-least-once guarantee here — it's closer to
  at-most-once for in-flight work).
- A consumer that's down when an event is published and only comes back up
  later will not see that event, since it starts from `latest`.

**What's missing, for anyone hardening this further:** explicit manual
offset commits after successful handling, a dead-letter topic for
handler exceptions, idempotency keys on events (so a redelivered
`order-created` doesn't push duplicate WebSocket messages to a
restaurant), and a producer-side retry/outbox pattern so a Kafka hiccup
doesn't silently drop an event the rest of the workflow depends on.

---

## 5. Data Consistency Approach

This system uses **eventual consistency via choreography**, not strong
consistency via a coordinator:

- There is **no saga orchestrator** and **no distributed transaction**
  tying `order-created` → `res-available` → `Order-placed` together. Each
  service decides independently, based on the events it sees, what state
  it's in.
- There are **no compensating actions**. If a restaurant rejects an order
  (or only partially accepts a multi-restaurant cart), the Restaurant
  Manager still emits `res-available` with `flag: false`, but nothing in
  the codebase currently unwinds the order, refunds anything, or notifies
  restaurants that already accepted that the rest of the order fell
  through.
- **State is fragmented and ephemeral.** Order state lives in three
  separate, unsynchronized in-memory dictionaries — one in the Order
  Service, one in the Restaurant Manager, one in the Delivery Route
  Service — none of which are persisted. A restart of any one service
  loses that service's view of all in-flight orders, even though the other
  two services may still think the order is active.
- **The only durable store** in the entire system is the Restaurant
  Manager's PostgreSQL database, and it holds only restaurant/dish
  reference data — not order or delivery state.
- **No idempotency.** Nothing in the event payloads (no event ID, no
  order version) lets a consumer detect and discard a duplicate or
  redelivered event. The "wait for 2 signals" aggregation pattern in the
  Order Service is a simple counter, not a tracked set of which specific
  event types have arrived — so out-of-order or duplicate deliveries of
  the same topic could trigger `Order-placed` prematurely or twice.

**In short:** the architecture demonstrates the right shape for an
event-driven, choreographed order workflow, but the current implementation
optimizes for showing the Kafka producer/consumer wiring and Docker
containerization clearly, not for production-grade durability. Anyone
extending this toward production should prioritize, in order: (1) durable
order state (a database for the Order Service and Delivery Route Service),
(2) manual offset commits tied to successful processing, (3) idempotency
keys on events, and (4) a dead-letter topic + alerting for handler
failures.
