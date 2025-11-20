import random
from captcha_recognizer.slider import Slider
from datetime import datetime, timezone, timedelta


class SliderTools:

    @classmethod
    def generate_human_track(cls, target_x):
        track_list = []

        current_t = random.randint(1000, 2000)
        start_y = random.randint(-1, 1)

        track_list.append({
            "x": 0,
            "y": start_y,
            "type": "down",
            "t": current_t
        })

        overshoot_x = target_x + random.randint(5, 20)
        current_y = start_y
        steps_to_overshoot = random.randint(20, 40)

        for i in range(steps_to_overshoot):
            time_delay = random.randint(10, 30)
            t_factor = (i + 1) / steps_to_overshoot
            ease_factor = 1 - (1 - t_factor) ** 2

            current_x = int(overshoot_x * ease_factor)
            current_y = start_y + random.randint(-1, 1)
            current_t += time_delay

            track_list.append({
                "x": current_x,
                "y": current_y,
                "type": "move",
                "t": current_t
            })

        correction_start_x = overshoot_x
        steps_to_correct = random.randint(5, 15)

        for i in range(steps_to_correct):
            time_delay = random.randint(30, 80)
            t_factor = (i + 1) / steps_to_correct

            current_x = int(correction_start_x - (correction_start_x - target_x) * t_factor)
            current_y = current_y + random.randint(-2, 2)
            current_t += time_delay

            track_list.append({
                "x": current_x,
                "y": current_y,
                "type": "move",
                "t": current_t
            })

        time_delay = random.randint(50, 200)
        current_t += time_delay
        track_list.append({
            "x": target_x,
            "y": current_y,
            "type": "move",
            "t": current_t
        })

        time_delay = random.randint(200, 500)
        current_t += time_delay
        track_list.append({
            "x": target_x,
            "y": current_y,
            "type": "up",
            "t": current_t
        })

        return track_list

    @classmethod
    def create_check_payload(cls, target_x, width=300, height=180):
        track_list = cls.generate_human_track(target_x)

        last_t = track_list[-1]['t']

        stop_time_dt = datetime.now(timezone.utc)

        start_time_dt = stop_time_dt - timedelta(milliseconds=last_t)

        def format_iso_time(dt):
            return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        start_time_iso = format_iso_time(start_time_dt)
        stop_time_iso = format_iso_time(stop_time_dt)

        check_query = {
            "bgImageWidth": width,
            "bgImageHeight": height,
            "startTime": start_time_iso,
            "stopTime": stop_time_iso,
            "trackList": track_list
        }
        return check_query

    @classmethod
    def get_slider_data(cls, bg_bytes):
        return Slider().identify(source=bg_bytes)

    @classmethod
    def get_trace_data(cls, code, width=300, height=180):
        return cls.create_check_payload(target_x=code, width=width, height=height)
