import asyncio

import httpx
from fastapi import FastAPI, HTTPException

import manager
from consumer import consume
from producer import start_producer, stop_producer
from fastapi.responses import HTMLResponse

app = FastAPI(title="Delivery Route Service")

ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjYwMGZlYzVlMDU2NjY2MmI1NzZiNGIzNjMxYjczZGU5MGVhOGUyZTc1OWQwMjg1YTA1YmQyNWI3IiwiaCI6Im11cm11cjY0In0="  # replace with your key from openrouteservice.org
ORS_URL     = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"


# ── Lifecycle ────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    await start_producer()
    asyncio.create_task(consume())
    print("Producer started. Consumer task launched.")


@app.on_event("shutdown")
async def shutdown():
    await stop_producer()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _validate_coords(lat: float, lng: float, label: str):
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        raise HTTPException(400, f"Invalid {label} coordinates: lat={lat}, lng={lng}")
    if lat == 0.0 and lng == 0.0:
        raise HTTPException(400, f"{label} coordinates are 0,0 — likely uninitialized")


async def _fetch_ors_route(client: httpx.AsyncClient, origin: list, destination: list) -> dict:
    """
    Call ORS directions for a single origin→destination pair.
    origin / destination are [lat, lng] lists.
    ORS expects [lng, lat] order.
    """
    o_lat, o_lng = origin
    d_lat, d_lng = destination

    _validate_coords(o_lat, o_lng, "origin")
    _validate_coords(d_lat, d_lng, "destination")

    payload = {"coordinates": [[o_lng, o_lat], [d_lng, d_lat]]}
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}

    try:
        resp = await client.post(ORS_URL, json=payload, headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"ORS API error: {e.response.text}",
        )
    return resp.json()


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/getLocation/{oid}")
async def get_location(oid: str):
    """
    Fetch two routes for an order:
      route1 — delivery-person location  →  restaurant location
      route2 — restaurant location       →  order (customer) location

    order_info shape expected in manager.order_status[oid]:
    {
        "res-available":  {"res_id": int, "location": [lat, lng]},
        "del location":   [lat, lng],
        "order-location": [lat, lng]
    }
    """
    order_info = manager.order_status.get(oid)
    if not order_info:
        raise HTTPException(404, detail=f"Order '{oid}' not found. It may not have been placed yet.")

    res_id         = list(order_info["res_locations"].keys())[0]
    res_location   = order_info["res_locations"][res_id]
    del_location   = order_info["del_location"]
    order_location = order_info["order_location"]

    async with httpx.AsyncClient(timeout=15) as client:
        route1, route2 = await asyncio.gather(
            _fetch_ors_route(client, del_location,   res_location),    # del → res
            _fetch_ors_route(client, res_location,   order_location),  # res → order
        )

    return {
        "order_id":    oid,
        "order_info":  order_info,
        "routes": {
            "route1_del_to_res":    route1,   # delivery person picks up from restaurant
            "route2_res_to_order":  route2,   # restaurant to customer
        },
    }


@app.get("/status/{oid}")
async def get_order_status(oid: str):
    """Quick check — returns the raw stored order_info for an order."""
    info = manager.order_status.get(oid)
    if not info:
        raise HTTPException(404, detail=f"Order '{oid}' not tracked yet.")
    return {"order_id": oid, "order_info": info}


@app.get("/health")
async def health():
    return {"status": "ok", "tracked_orders": len(manager.order_status)}

@app.get("/map/{oid}", response_class=HTMLResponse)
async def get_map(oid: str):
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <title>Order {oid} Routes</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style> #map {{ height: 100vh; margin: 0; }} </style>
</head>
<body>
<div id="map"></div>
<script>
const map = L.map('map');
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);

fetch('/getLocation/{oid}')
  .then(r => r.json())
  .then(data => {{
    const routes = data.routes;

    // Route 1: delivery → restaurant (blue)
    const r1 = L.geoJSON(routes.route1_del_to_res, {{color: 'blue', weight: 5}}).addTo(map);
    // Route 2: restaurant → customer (green)
    const r2 = L.geoJSON(routes.route2_res_to_order, {{color: 'green', weight: 5}}).addTo(map);

    // Markers
    const info = data.order_info;
    const resId  = Object.keys(info.res_locations)[0];
    const resLoc = info.res_locations[resId];
    const delLoc = info.del_location;
    const ordLoc = info.order_location;

    L.marker([resLoc[0], resLoc[1]]).addTo(map).bindPopup('🍽️ Restaurant').openPopup();
    L.marker([delLoc[0], delLoc[1]]).addTo(map).bindPopup('🛵 Delivery Person');
    L.marker([ordLoc[0], ordLoc[1]]).addTo(map).bindPopup('📦 Customer');

    // Fit map to routes
    const group = L.featureGroup([r1, r2]);
    map.fitBounds(group.getBounds(), {{padding: [40, 40]}});
  }})
  .catch(e => document.body.innerHTML = '<h2>Error: ' + e + '</h2>');
</script>
</body>
</html>
"""
