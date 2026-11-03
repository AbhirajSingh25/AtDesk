from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

class DynamicEtaService:
    @staticmethod
    def calculate_eta(
        shop_prep_times: List[int],
        num_shops: int,
        tower: str,
        floor: int,
        is_scheduled: bool = False,
        scheduled_target_time: datetime = None
    ) -> Dict[str, Any]:
        """
        Calculates dynamic ETA adhering to Part 9 & 10:
        1. Does not simply sum prep times because shops prepare in parallel!
           Effective prep time = max(prep_times) + small staggered coordination buffer.
        2. Travel time between shops inside JMD Megapolis plaza (2 mins per additional shop).
        3. Runner collection and packaging buffer (3-5 mins).
        4. Building security and elevator transit to Tower (Tower A/B/C/D) + floor (approx 20s per floor).
        5. Desk handover buffer (2 mins).
        """
        if not shop_prep_times:
            shop_prep_times = [10]

        # 1. Overlapped preparation: maximum single shop prep time + 2 min coordination delta per extra shop
        max_prep = max(shop_prep_times)
        extra_shops_coordination = max(0, num_shops - 1) * 2
        effective_prep_mins = max_prep + extra_shops_coordination

        # 2. Travel between shops in JMD Megapolis ground concourse
        travel_between_shops = max(0, num_shops - 1) * 2

        # 3. Runner pickup and packaging check
        runner_pickup_buffer = 4

        # 4. Building security + elevator access (JMD Megapolis Tower A/B/C/D)
        # Floor transit: base 3 mins + 0.3 mins per floor
        building_elevator_transit = 3 + int(floor * 0.3)

        # 5. Desk walk & handover
        desk_handover_buffer = 2

        total_nominal_mins = (
            effective_prep_mins +
            travel_between_shops +
            runner_pickup_buffer +
            building_elevator_transit +
            desk_handover_buffer
        )

        min_eta_mins = max(15, total_nominal_mins - 3)
        max_eta_mins = total_nominal_mins + 5

        now = datetime.now(timezone.utc)
        estimated_delivery_time = now + timedelta(minutes=total_nominal_mins)
        start_win = now + timedelta(minutes=min_eta_mins)
        end_win = now + timedelta(minutes=max_eta_mins)

        # Formatted window e.g., "25 - 35 mins (by 08:15 PM)"
        window_str = f"{min_eta_mins} - {max_eta_mins} mins"

        return {
            "min_eta_mins": min_eta_mins,
            "max_eta_mins": max_eta_mins,
            "estimated_arrival_window": window_str,
            "preparation_overlap_mins": effective_prep_mins,
            "travel_between_shops_mins": travel_between_shops,
            "runner_building_access_mins": building_elevator_transit,
            "floor_and_desk_handover_mins": desk_handover_buffer,
            "total_estimated_mins": total_nominal_mins,
            "estimated_delivery_time": estimated_delivery_time,
            "factors": {
                "max_individual_shop_prep": max_prep,
                "multi_shop_coordination": extra_shops_coordination,
                "floor_level": floor,
                "destination_tower": tower,
                "shops_involved_count": num_shops
            }
        }

