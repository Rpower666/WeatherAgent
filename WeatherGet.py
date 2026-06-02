import json
import os
from urllib.parse import quote

import requests
from dotenv import load_dotenv

try:
    from .WeatherApiPath import WEATHER_API_PATHS
    from .WeatherGetEncode import encoder
except ImportError:
    from WeatherApiPath import WEATHER_API_PATHS
    from WeatherGetEncode import encoder


class weather:
    def __init__(
        self,
        hostApi: str = None,
        location: str = None,
        encoded_jwt: str = None,
        api_name: str = "weather_24h",
    ):
        load_dotenv()
        self.hostApi = hostApi or os.getenv("HOST_API")
        self.location_str = location
        self.encoded_jwt = encoded_jwt or encoder().encodeJWT()
        self.api_name = api_name

    def _request(self, api_name: str, *args: str) -> dict:
        api_path = WEATHER_API_PATHS[api_name]
        quoted_args = [quote(arg or "") for arg in args]
        url = f"https://{self.hostApi}{api_path.format(*quoted_args)}"
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {self.encoded_jwt}",
                "Accept-Encoding": "gzip",
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def _parse_location(self) -> tuple[str, str]:
        location = (self.location_str or "").strip()
        city_suffix_index = location.find("市")
        if city_suffix_index != -1 and city_suffix_index < len(location) - 1:
            adm = location[:city_suffix_index + 1]
            location = location[city_suffix_index + 1:]
            return location, adm
        return location, ""

    def get_agent_guide(self) -> dict:
        return {
            "purpose": "先把用户输入的位置转换为和风天气标准 location id，再用 id 查询天气。",
            "flow": [
                "解析用户输入的位置，例如 成都市彭州市 -> location=彭州市, adm=成都市。",
                "调用 city_lookup: /geo/v2/city/lookup?location={0}&adm={1}。",
                "从返回 JSON 的 location[0].id 中取标准城市 ID，例如 101010100。",
                f"调用天气接口 {self.api_name}: {WEATHER_API_PATHS[self.api_name]}。",
                "把返回 JSON 转成 Markdown 表格、来源 URL 和天气建议。",
            ],
            "output_fields": {
                "location_info": "位置查询返回的标准城市信息。",
                "weather_data": "天气接口返回的原始 JSON。",
                "source_url": "和风天气返回的 fxLink，可发给用户查看详情。",
                "visualization": "给用户看的 Markdown 文本或表格。",
                "advice": "根据天气数据生成的出行和穿衣建议。",
                "message": "可以直接发送给用户的完整消息。",
            },
        }

    def locationGet(self) -> dict:
        location, adm = self._parse_location()
        data = self._request("city_lookup", location, adm)
        locations = data.get("location", [])
        if not locations:
            raise ValueError(f"未查询到位置: {self.location_str}")
        return locations[0]

    def weatherGet(self) -> tuple[dict | None, str | None]:
        try:
            location_info = self.locationGet()
            data = self._request(self.api_name, location_info["id"])
            return data, data.get("fxLink")
        except (KeyError, ValueError) as e:
            print(e)
        return None, None

    def get_weather_payload(self) -> dict:
        location_info = self.locationGet()
        location_id = location_info["id"]
        data = self._request(self.api_name, location_id)
        weather_now = None
        if "daily" in data:
            try:
                weather_now = self._request("weather_now", location_id)
            except (KeyError, requests.RequestException) as e:
                print(e)
        source_url = data.get("fxLink")
        visualization = self.to_markdown_table(data, weather_now=weather_now)
        advice = self.build_advice(data)
        message = self.build_user_message(
            location_name=location_info.get("name", self.location_str),
            data=data,
            source_url=source_url,
            visualization=visualization,
            advice=advice,
        )
        return {
            "location_info": location_info,
            "weather_data": data,
            "weather_now": weather_now,
            "source_url": source_url,
            "visualization": visualization,
            "advice": advice,
            "message": message,
            "agent_guide": self.get_agent_guide(),
        }

    def to_json_text(self, data: dict) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2)

    def to_markdown_table(self, data: dict, weather_now: dict | None = None) -> str:
        if not data:
            return "没有可展示的天气数据。"

        if "hourly" in data:
            rows = [
                "| 时间 | 天气 | 温度 | 风向 | 风力 | 湿度 | 降水概率 |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
            for item in data["hourly"]:
                rows.append(
                    "| {time} | {text} | {temp}℃ | {wind_dir} | {wind_scale}级 | {humidity}% | {pop}% |".format(
                        time=item.get("fxTime", ""),
                        text=item.get("text", ""),
                        temp=item.get("temp", ""),
                        wind_dir=item.get("windDir", ""),
                        wind_scale=item.get("windScale", ""),
                        humidity=item.get("humidity", ""),
                        pop=item.get("pop", ""),
                    )
                )
            return "\n".join(rows)

        if "daily" in data:
            feels_like = ""
            if weather_now and "now" in weather_now:
                feels_like_value = weather_now["now"].get("feelsLike", "")
                if feels_like_value not in (None, ""):
                    feels_like = f"{feels_like_value}℃"
            rows = [
                "| 日期 | 白天 | 夜间 | 最高温 | 最低温 | 体感温度 | 风向 | 风力 | 紫外线 | 湿度 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
            for index, item in enumerate(data["daily"]):
                rows.append(
                    "| {date} | {day} | {night} | {max_temp}℃ | {min_temp}℃ | {feels_like} | {wind_dir} | {wind_scale}级 | {uv} | {humidity}% |".format(
                        date=item.get("fxDate", ""),
                        day=item.get("textDay", ""),
                        night=item.get("textNight", ""),
                        max_temp=item.get("tempMax", ""),
                        min_temp=item.get("tempMin", ""),
                        feels_like=feels_like if index == 0 else "",
                        wind_dir=item.get("windDirDay", ""),
                        wind_scale=item.get("windScaleDay", ""),
                        uv=item.get("uvIndex", ""),
                        humidity=item.get("humidity", ""),
                    )
                )
            return "\n".join(rows)

        if "now" in data:
            now = data["now"]
            return (
                f"当前天气：{now.get('text', '')}\n"
                f"温度：{now.get('temp', '')}℃\n"
                f"体感温度：{now.get('feelsLike', '')}℃\n"
                f"风向：{now.get('windDir', '')}\n"
                f"风力：{now.get('windScale', '')}级\n"
                f"湿度：{now.get('humidity', '')}%"
            )

        return self.to_json_text(data)

    def build_advice(self, data: dict) -> list[str]:
        advice = []
        items = data.get("hourly") or data.get("daily") or []

        if "now" in data:
            items = [data["now"]]

        if self._has_weather_text(items, ("雨", "雪", "雷", "阵雨")):
            advice.append("可能有降水，建议带伞，出行注意路面湿滑。")

        max_temp = self._max_number(items, ("temp", "tempMax"))
        min_temp = self._min_number(items, ("temp", "tempMin", "feelsLike"))
        max_pop = self._max_number(items, ("pop",))
        max_wind = self._max_number(items, ("windScale", "windScaleDay"))
        max_uv = self._max_number(items, ("uvIndex",))

        if max_pop is not None and max_pop >= 60:
            advice.append(f"降水概率最高约 {max_pop}% ，建议安排室内备选方案。")
        if max_temp is not None and max_temp >= 30:
            advice.append("气温较高，注意补水、防晒，减少长时间户外暴晒。")
        if min_temp is not None and min_temp <= 10:
            advice.append("气温偏低，建议增加保暖衣物。")
        if max_wind is not None and max_wind >= 5:
            advice.append("风力较大，骑行和高处活动需要注意安全。")
        if max_uv is not None and max_uv >= 6:
            advice.append("紫外线较强，建议使用防晒用品。")

        if not advice:
            advice.append("天气条件整体平稳，正常安排出行即可。")
        return advice

    def build_user_message(
        self,
        location_name: str,
        data: dict,
        source_url: str | None,
        visualization: str,
        advice: list[str],
    ) -> str:
        lines = [
            f"## {location_name}天气",
            "",
            visualization,
            "",
            "### 建议",
        ]
        lines.extend(f"- {item}" for item in advice)
        if source_url:
            lines.extend(["", f"详情链接：{source_url}"])
        if data and data.get("updateTime"):
            lines.append(f"更新时间：{data['updateTime']}")
        return "\n".join(lines)

    def _has_weather_text(self, items: list[dict], keywords: tuple[str, ...]) -> bool:
        text_fields = ("text", "textDay", "textNight")
        for item in items:
            text = "".join(str(item.get(field, "")) for field in text_fields)
            if any(keyword in text for keyword in keywords):
                return True
        return False

    def _max_number(self, items: list[dict], keys: tuple[str, ...]) -> int | None:
        values = self._numbers(items, keys)
        return max(values) if values else None

    def _min_number(self, items: list[dict], keys: tuple[str, ...]) -> int | None:
        values = self._numbers(items, keys)
        return min(values) if values else None

    def _numbers(self, items: list[dict], keys: tuple[str, ...]) -> list[int]:
        values = []
        for item in items:
            for key in keys:
                value = item.get(key)
                if value in (None, ""):
                    continue
                try:
                    values.append(int(str(value).split("-")[0]))
                except ValueError:
                    continue
        return values


if __name__ == "__main__":
    client = weather(location="成都市彭州市", api_name="weather_3d")
    payload = client.get_weather_payload()
    print(payload["message"])
