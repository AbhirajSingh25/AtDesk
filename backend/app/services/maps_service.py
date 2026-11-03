import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import logging

from backend.app.core.config import settings

logger = logging.getLogger("atdesk.maps_service")

# JMD Megapolis Sector 48 Gurugram Spatial Coordinate Model
JMD_COORDINATES = {
    "CENTER": {"lat": 28.41620, "lng": 77.04250},
    "TOWERS": {
        "Tower A": {"lat": 28.41640, "lng": 77.04230, "gate": "North Entry", "security_check_mins": 3},
        "Tower B": {"lat": 28.41630, "lng": 77.04280, "gate": "East Entry", "security_check_mins": 3},
        "Tower C": {"lat": 28.41590, "lng": 77.04270, "gate": "South Entry", "security_check_mins": 3},
        "Tower D": {"lat": 28.41580, "lng": 77.04220, "gate": "West Entry", "security_check_mins": 3},
    },
    "SHOPS": {
        1: {"name": "Chaayos", "lat": 28.41615, "lng": 77.04245, "level": "Ground Floor", "handover_buffer_mins": 2},
        2: {"name": "Haldiram's Express", "lat": 28.41625, "lng": 77.04255, "level": "Ground Floor", "handover_buffer_mins": 2},
        3: {"name": "Starbucks Coffee", "lat": 28.41610, "lng": 77.04260, "level": "Ground Floor", "handover_buffer_mins": 2},
        4: {"name": "Subway Fresh", "lat": 28.41630, "lng": 77.04240, "level": "Ground Floor", "handover_buffer_mins": 2},
        5: {"name": "The Daily Desk Essentials", "lat": 28.41622, "lng": 77.04248, "level": "Ground Floor", "handover_buffer_mins": 1},
    }
}

class MapsService:
    """
    Google Maps Platform & JMD Megapolis Campus Routing Engine.
    Provides:
    - Accurate geospatial distances within commercial campus.
    - Optimal multi-shop collection route sequencing.
    - Campus vertical transit buffers (Tower entry, elevator, floor walk).
    - GPS location freshness categorization.
    - Live tracking gate (only tracks during active assigned orders).
    """

    @staticmethod
    def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates ground distance in meters between two coordinates"""
        R = 6371000  # Radius of earth in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2.0) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c

    @staticmethod
    def get_location_freshness(last_ping_time: Optional[datetime]) -> Dict[str, Any]:
        """
        Determines freshness of GPS signal:
        - delta < 30s: LIVE (solid real-time)
        - 30s <= delta <= 120s: RECENT (active walking)
        - delta > 120s: STALE (elevator/corridor signal shadow)
        """
        if not last_ping_time:
            return {
                "freshness": "UNKNOWN",
                "is_live": False,
                "description": "No recent GPS signal recorded",
                "seconds_ago": None
            }

        now = datetime.now(timezone.utc)
        if last_ping_time.tzinfo is None:
            last_ping_time = last_ping_time.replace(tzinfo=timezone.utc)

        delta_seconds = int((now - last_ping_time).total_seconds())

        if delta_seconds < 30:
            return {
                "freshness": "LIVE",
                "is_live": True,
                "description": f"Live GPS update ({delta_seconds}s ago)",
                "seconds_ago": delta_seconds
            }
        elif delta_seconds <= 120:
            return {
                "freshness": "RECENT",
                "is_live": True,
                "description": f"GPS signal updated {delta_seconds}s ago",
                "seconds_ago": delta_seconds
            }
        else:
            return {
                "freshness": "STALE",
                "is_live": False,
                "description": f"GPS signal stale ({int(delta_seconds / 60)}m ago) - Runner inside elevator or basement corridor",
                "seconds_ago": delta_seconds
            }

    @staticmethod
    def optimize_pickup_sequence(
        runner_lat: float,
        runner_lng: float,
        shop_ids: List[int],
        destination_tower: str
    ) -> Dict[str, Any]:
        """
        Calculates optimal pickup sequence:
        Runner -> Nearest Shop -> Next Shops -> Destination Tower.
        """
        shops = []
        for sid in shop_ids:
            s_info = JMD_COORDINATES["SHOPS"].get(sid, {
                "name": f"Shop {sid}",
                "lat": JMD_COORDINATES["CENTER"]["lat"],
                "lng": JMD_COORDINATES["CENTER"]["lng"],
                "level": "Ground Floor",
                "handover_buffer_mins": 2
            })
            shops.append({"shop_id": sid, **s_info})

        # Greedy nearest neighbor sequence
        unvisited = list(shops)
        current_lat, current_lng = runner_lat, runner_lng
        ordered_stops = []
        total_walking_meters = 0.0

        while unvisited:
            nearest = min(
                unvisited,
                key=lambda s: MapsService.haversine_distance_meters(current_lat, current_lng, s["lat"], s["lng"])
            )
            dist = MapsService.haversine_distance_meters(current_lat, current_lng, nearest["lat"], nearest["lng"])
            total_walking_meters += dist
            ordered_stops.append(nearest)
            current_lat, current_lng = nearest["lat"], nearest["lng"]
            unvisited.remove(nearest)

        # Distance to target tower
        tower_info = JMD_COORDINATES["TOWERS"].get(destination_tower, JMD_COORDINATES["TOWERS"]["Tower A"])
        tower_dist = MapsService.haversine_distance_meters(current_lat, current_lng, tower_info["lat"], tower_info["lng"])
        total_walking_meters += tower_dist

        # Walking speed: ~1.2 meters per second in complex
        walking_time_mins = math.ceil(total_walking_meters / (1.2 * 60))
        shop_handovers = sum(s.get("handover_buffer_mins", 2) for s in ordered_stops)

        return {
            "ordered_stops": ordered_stops,
            "destination_tower": destination_tower,
            "total_walking_distance_meters": round(total_walking_meters, 1),
            "estimated_walking_time_mins": walking_time_mins,
            "shop_handover_buffers_mins": shop_handovers
        }

    @staticmethod
    def calculate_campus_eta(
        runner_lat: float,
        runner_lng: float,
        shop_ids: List[int],
        tower: str,
        floor: int,
        max_prep_time_mins: int
    ) -> Dict[str, Any]:
        """
        Calculates comprehensive campus delivery ETA:
        Max Prep Time + Multi-Shop Collection Walking + Shop Handovers + Tower Gate Security + Vertical Elevator Walk.
        """
        route = MapsService.optimize_pickup_sequence(runner_lat, runner_lng, shop_ids, tower)
        
        # Tower entry & vertical buffer
        tower_info = JMD_COORDINATES["TOWERS"].get(tower, JMD_COORDINATES["TOWERS"]["Tower A"])
        gate_security_mins = tower_info.get("security_check_mins", 3)
        floor_transit_mins = math.ceil(max(0, floor - 1) * 0.5) + 1  # 30 sec per floor + corridor walk

        total_transit_mins = (
            route["estimated_walking_time_mins"] +
            route["shop_handover_buffers_mins"] +
            gate_security_mins +
            floor_transit_mins
        )

        min_total_mins = max(max_prep_time_mins, total_transit_mins)
        max_total_mins = min_total_mins + 8  # 8 min variance window

        return {
            "min_eta_mins": min_total_mins,
            "max_eta_mins": max_total_mins,
            "route_breakdown": {
                "max_shop_prep_mins": max_prep_time_mins,
                "walking_distance_meters": route["total_walking_distance_meters"],
                "shop_pickup_walking_mins": route["estimated_walking_time_mins"],
                "shop_handovers_mins": route["shop_handover_buffers_mins"],
                "tower_gate_security_mins": gate_security_mins,
                "vertical_floor_elevator_mins": floor_transit_mins
            },
            "pickup_stops": [s["name"] for s in route["ordered_stops"]],
            "destination": f"{tower}, Floor {floor}"
        }

