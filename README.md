# Food Delivery — Event-Driven Backend (Kafka)

A microservices-based food delivery backend built around **Apache Kafka** as the
event backbone. Order placement, restaurant acceptance, and delivery-route
generation are decoupled into independent FastAPI services that communicate
almost entirely through Kafka topics rather than direct synchronous calls.

This documentation covers the three core services — **Order Service**,
**Restaurant Manager**, and **Delivery Route Service** — along with the
shared frontend and the per-service Docker Compose setup.

---

## 1. System Overview

```
                 ┌──────────────────┐
   Customer ───► │  Order Service    │ ───POST /Order──┐
   (browser)     │  (OrderManager)   │                 │
                 └─────────▲─────────┘                 ▼
                           │                     produces "order-created"
                       WS /ws                            │
                           │                              ▼
                 ┌─────────┴─────────┐          ┌───────────────────┐
                 │   Kafka Broker     │ ◄──────► │ Restaurant Manager │
                 │   (kafka:9092)     │          │   (ResManager)     │
                 └─────────▲─────────┘          └─────────▲──────────┘
                           │                                │
                  consumes "Order-placed"            WS to restaurant
                           │                          dashboard clients
                           ▼
                 ┌───────────────────┐
                 │ Delivery Route Svc │ ──HTTP──► OpenRouteService API
                 │ (delivery_route)   │
                 └───────────────────┘
```

Each service is an independent FastAPI application with its own producer,
consumer, and Docker container. Services coordinate by publishing and
reacting to Kafka events rather than calling each other's business logic
directly. The one exception is a single synchronous HTTP call the Order
Service makes to the Restaurant Manager to resolve a restaurant's
coordinates before placing an order (see §8).

---

## 2. Why Event-Driven

- **Decoupling:** the Order Service doesn't need to know how the Restaurant
  Manager decides whether a restaurant accepts an order — it just reacts to
  a `res-available` event.
- **Parallel reactions:** both the Restaurant Manager and the Delivery Route
  Service react to the same `Order-placed` event independently, with no
  coordination code between them.
- **Asynchronous, long-running steps:** restaurant acceptance takes time.
  Kafka lets that happen in the background while the customer gets
  immediate confirmation that their order was received, with live status
  pushed over a WebSocket as the workflow progresses.
- **Extensible by design:** new consumers (notifications, analytics, a
  delivery-partner matching service) can subscribe to existing topics
  without any changes to the producers.

---

## 3. Services

### 3.1 Order Service (`OrderManager`)

The customer-facing entry point. Accepts the cart, drives the order
workflow forward, and pushes live status updates to the customer over a
WebSocket.

**Responsibilities**
- Expose `POST /Order` to accept a cart and start an order.
- Resolve each restaurant's lat/long via an HTTP call to the Restaurant
  Manager.
- Generate the customer drop-off location.
- Publish `order-created`.
- Consume `res-available` and `Del-available`, aggregate them per order,
  and once the order is fully confirmed, publish `Order-placed`.
- Push live order status to the connected customer over `WS /ws`.

**State:** kept in-memory (`order_status`, `Event_counter`) for fast,
low-latency lookups during an order's lifecycle.

### 3.2 Restaurant Manager (`ResManager`)

Owns restaurant and dish data, authenticates restaurant accounts, and
manages the live conversation with restaurants over a WebSocket as orders
come in.

**Responsibilities**
- Restaurant auth (register/login/JWT) and restaurant/dish CRUD, backed by
  PostgreSQL via SQLAlchemy.
- Expose restaurant coordinates via `GET /res/restaurants/{id}` (called by
  the Order Service).
- Maintain a WebSocket per connected restaurant (`/communicate/ws`) used to
  push incoming orders to the restaurant dashboard and receive
  accept/confirm signals back.
- Consume `order-created`: push the order to the relevant restaurant
  socket(s), track acceptance, then publish `res-available` with a `flag`
  indicating whether every restaurant in the cart accepted.
- Consume `Order-placed`: push a final confirmation to the restaurant
  socket(s).

**State:** PostgreSQL (`restaurants`, `dishes` tables) for restaurant/dish
data; an in-memory registry for live restaurant WebSocket connections and
per-order acceptance status.

### 3.3 Delivery Route Service (`delivery_route_service`)

Turns a placed order into an actual driving route using the
OpenRouteService (ORS) API, and serves a live map for it.

**Responsibilities**
- Consume `Order-placed` and cache the order's locations
  (`res_locations`, `del_location`, `order_location`) for fast retrieval.
- `GET /getLocation/{oid}`: fetch two ORS driving routes in parallel —
  delivery person → restaurant, and restaurant → customer.
- `GET /map/{oid}`: serve a self-contained Leaflet/OpenStreetMap HTML page
  that renders both routes and pins for restaurant, delivery person, and
  customer.
- `GET /status/{oid}` and `GET /health` for order inspection and
  health-checking.

**State:** kept in-memory (`order_status`) for quick access during active
deliveries.

### Frontend

`static/ResAuth.html` is the single-page HTML/JS/CSS UI used for the
customer order-placement flow and the `WS /ws` connection for live order
status updates. It's served directly by FastAPI's `StaticFiles` mount —
no separate frontend build step or framework required.

---

## 4. Kafka Topics & Event Schemas

All topics carry JSON-encoded UTF-8 payloads, passed straight to
`AIOKafkaProducer.send()` / `AIOKafkaConsumer()`.

| Topic | Producer | Consumer(s) |
|---|---|---|
| `order-created` | Order Service | Restaurant Manager |
| `res-available` | Restaurant Manager | Order Service |
| `Order-placed` | Order Service | Restaurant Manager, Delivery Route Service |
| `Del-available` | Delivery-partner matching integration | Order Service |

`Del-available` is the integration point the Order Service uses to factor
delivery-partner assignment into the order-confirmation flow alongside
restaurant acceptance — useful for wiring in a dedicated delivery-matching
service as the platform grows.

### `order-created`
Published by the Order Service after a customer submits a cart.
```json
{
  "order_id": 42,
  "cart": { "1": [101, 102], "3": [205] },
  "Locations": { "1": [12.97, 77.59], "3": [12.95, 77.61] },
  "Destin": [12.971, 77.594]
}
```
- `cart`: dish IDs grouped by restaurant ID.
- `Locations`: restaurant ID → `[lat, long]`.
- `Destin`: customer drop-off `[lat, long]`.

### `res-available`
Published by the Restaurant Manager once it has decided whether every
restaurant in the order accepted.
```json
{
  "order_id": 42,
  "cart": { "1": [101, 102], "3": [205] },
  "flag": true
}
```
- `flag`: `true` only if every restaurant in the cart accepted the order.

### `Order-placed`
Published by the Order Service once the order is confirmed.
```json
{
  "order_id": 42,
  "cart": { "1": [101, 102], "3": [205] },
  "flag": true,
  "order_info": {
    "res_locations": { "1": [12.97, 77.59] },
    "order_location": [12.971, 77.594],
    "del_location": [12.98, 77.60]
  }
}
```
This is the payload the Delivery Route Service relies on to build routes —
`res_locations`, `del_location`, and `order_location` map directly to the
three points it draws on the map.

### `Del-available`
Shape expected by the Order Service's consumer:
```json
{
  "order_id": 42,
  "lat": 12.98,
  "long": 77.60,
  "flag": true
}
```

---

## 5. API Endpoints

### Order Service (`OrderManager`, host port `8001`)
| Method | Path | Description |
|---|---|---|
| POST | `/Order` | Submit a cart, kick off the order workflow, publish `order-created`. |
| GET | `/order-page` | Serve the static order-placement HTML page. |
| WS | `/ws` | Live order-status channel for the customer. |

### Restaurant Manager (`ResManager`, host port `8000`)
All routes are mounted under `/api/ResManager`.
| Method | Path | Description |
|---|---|---|
| POST | `/api/ResManager/auth/register` | Register a restaurant account. |
| POST | `/api/ResManager/auth/login` | Log in, returns a JWT bearer token. |
| GET | `/api/ResManager/auth/me` | Get the authenticated restaurant's profile. |
| WS | `/api/ResManager/communicate/ws?restaurant_id=&token=` | Restaurant dashboard socket: receives incoming orders, sends accept/confirm signals. |
| GET | `/api/ResManager/res/` | Serve the static restaurant auth/order page. |
| POST | `/api/ResManager/res/create-restaurant` | Create a restaurant. |
| GET | `/api/ResManager/res/restaurants` | List all restaurants. |
| GET | `/api/ResManager/res/restaurants/{id}` | Get a restaurant's live `lat`/`long` (used by the Order Service). |
| POST | `/api/ResManager/dishes/create-dish` | Create a dish (requires restaurant auth). |
| GET | `/api/ResManager/dishes/` | List the authenticated restaurant's own dishes. |
| GET | `/api/ResManager/dishes/all-dishes` | List every dish across all restaurants. |

### Delivery Route Service (`delivery_route`, host port `8003`)
| Method | Path | Description |
|---|---|---|
| GET | `/getLocation/{oid}` | Returns two GeoJSON routes (delivery→restaurant, restaurant→customer) via OpenRouteService. |
| GET | `/map/{oid}` | Renders a Leaflet/OpenStreetMap HTML page with both routes and markers. |
| GET | `/status/{oid}` | Returns the cached `order_info` for an order. |
| GET | `/health` | Basic health check + count of tracked orders. |

---

## 6. Running Locally with Docker

Each service ships its own `docker-compose.yml` and joins a shared
**external** Docker network, `app-net`, alongside a Kafka broker reachable
as `kafka:9092` on that network.

```bash
# 1. Create the shared network once
docker network create app-net

# 2. Start a Kafka broker on that network
cat > docker-compose.kafka.yml <<'EOF'
version: "3.9"
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    networks: [app-net]
  kafka:
    image: confluentinc/cp-kafka:7.6.0
    depends_on: [zookeeper]
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    networks: [app-net]
networks:
  app-net:
    external: true
    name: app-net
EOF
docker compose -f docker-compose.kafka.yml up -d

# 3. Start the Restaurant Manager (needs Postgres + .env, see §7)
cd ResManager && docker compose up --build -d

# 4. Start the Order Service
cd ../OrderManager && docker compose up --build -d

# 5. Start the Delivery Route Service
cd ../delivery_route_service/delivery_route && docker compose up --build -d
```

Once everything is up:
- Order Service: `http://localhost:8001`
- Restaurant Manager: `http://localhost:8000`
- Delivery Route Service: `http://localhost:8003`

Recommended startup order: **Kafka → Restaurant Manager → Order Service →
Delivery Route Service.** Each consumer reconnects automatically with a
3-second retry if the broker isn't reachable yet on first boot.

---

## 7. Environment Variables

| Variable | Used by | Notes |
|---|---|---|
| `DATABASE_URL` | Restaurant Manager | PostgreSQL connection string, loaded via `python-dotenv` from a `.env` file referenced in `docker-compose.yml`. |
| Kafka bootstrap address (`kafka:9092`) | All three services | Configured in each service's `Producer.py`/`Consumer.py`. |
| ORS API key | Delivery Route Service | Configured in `main.py` for the OpenRouteService Directions API integration. |
| JWT `SECRET_KEY` | Restaurant Manager | Configured in `Config/Security.py`, used to sign and verify restaurant auth tokens. |

---

## 8. Order Lifecycle: Placement → Delivery Tracking

1. **Customer places an order.** The frontend POSTs a cart
   (`[[dish_id, restaurant_id], ...]`) to the Order Service's `POST /Order`.
2. **Order Service resolves restaurant locations.** For each distinct
   restaurant in the cart, it calls the Restaurant Manager
   (`/api/ResManager/res/restaurants/{id}`) to get current lat/long, and
   generates the customer drop-off location.
3. **`order-created` is published.** The Order Service stores order state
   (`res_locations`, `order_location`) and returns `{"Status": "Requested"}`
   to the HTTP caller immediately.
4. **Restaurant Manager reacts.** It pushes the order to each restaurant's
   live WebSocket dashboard connection and tracks acceptance as restaurants
   respond.
5. **`res-available` is published**, carrying a `flag` for whether the
   whole order was accepted.
6. **Order Service confirms the order.** It aggregates `res-available` and
   `Del-available` signals per order, then publishes `Order-placed` with
   the full `order_info` bundle (restaurant locations, customer location,
   delivery location) and pushes a status update to the customer over
   `WS /ws`.
7. **Two services react to `Order-placed` in parallel:**
   - The **Restaurant Manager** sends a final confirmation message down the
     restaurant's WebSocket.
   - The **Delivery Route Service** caches `order_info` in memory, keyed by
     order ID.
8. **Delivery tracking.** The frontend hits
   `GET /map/{order_id}` on the Delivery Route Service, which calls
   OpenRouteService twice — delivery-person→restaurant and
   restaurant→customer — and renders both legs on a Leaflet map with pins
   for the restaurant, the delivery person, and the customer.
