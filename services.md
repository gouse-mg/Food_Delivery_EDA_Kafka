# Services Reference

| | Order Service (`OrderManager`) | Restaurant Manager (`ResManager`) | Delivery Route Service (`delivery_route_service`) |
|---|---|---|---|
| **Host port** | `8001` (maps to container port `8000`) | `8000` (maps to container port `8000`) | `8003` (maps to container port `8000`) |
| **Tech stack** | FastAPI, `aiokafka`, `httpx`, raw WebSockets, Pydantic | FastAPI, `aiokafka`, SQLAlchemy + PostgreSQL (`psycopg2-binary`), `python-jose` (JWT), `passlib[bcrypt]`, raw WebSockets | FastAPI, `aiokafka`, `httpx` (calls OpenRouteService) |
| **Kafka topics produced** | `order-created`, `Order-placed` | `res-available` | *(none — consumer only)* |
| **Kafka topics consumed** | `res-available`, `Del-available`¹ | `order-created`, `Order-placed` | `Order-placed` |
| **Consumer group ID** | `orderapi-group` | `resmanager-group-test` | `route-service-group` |
| **Database owned** | None — in-memory `order_status` / `Event_counter` dicts only | PostgreSQL: `restaurants`, `dishes` tables | None — in-memory `order_status` dict only |
| **Key HTTP endpoints** | `POST /Order`, `GET /order-page` | `POST /api/ResManager/auth/register`, `POST /api/ResManager/auth/login`, `GET /api/ResManager/auth/me`, `POST /api/ResManager/res/create-restaurant`, `GET /api/ResManager/res/restaurants`, `GET /api/ResManager/res/restaurants/{id}`, `POST /api/ResManager/dishes/create-dish`, `GET /api/ResManager/dishes/`, `GET /api/ResManager/dishes/all-dishes` | `GET /getLocation/{oid}`, `GET /map/{oid}`, `GET /status/{oid}`, `GET /health` |
| **WebSocket endpoints** | `WS /ws` (customer live status) | `WS /api/ResManager/communicate/ws?restaurant_id=&token=` (restaurant dashboard) | None |
| **External integrations** | None | None | OpenRouteService Directions API (`api.openrouteservice.org`) |
| **Static frontend** | `static/ResAuth.html` (and supporting `frontend.css/js`, `order.html`) | `static/ResAuth.html` (and supporting `frontend.css/js`, `order.html`) | None — `/map/{oid}` renders an inline Leaflet HTML page generated server-side |

¹ `Del-available` is subscribed to and handled by the Order Service, but no
service in this codebase's reviewed scope produces it — see `README.md` §4
and `ARCHITECTURE.md` §2 for details.

---

## Docker Compose Summary

| Service | Compose service name | Network |
|---|---|---|
| Order Service | `order-api` | `app-net` (external) |
| Restaurant Manager | `resmanager` | `app-net` (external) |
| Delivery Route Service | `route-api` | `app-net` (external) |

All three Compose files declare `app-net` as an **external** network, so it
must be created once up front (`docker network create app-net`) before any
of the services are started. None of the three Compose files define a
Kafka or Zookeeper service — a broker reachable at `kafka:9092` on
`app-net` is assumed to exist already (see `README.md` §6 for a sample
broker Compose snippet).
