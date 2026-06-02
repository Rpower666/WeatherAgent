# Weather Agent

`ExampleAgent` 提供了一个和风天气查询示例，支持让 Agent 理解天气数据获取流程、查询天气、把 JSON 可视化为 Markdown，并返回天气详情 URL 和出行建议。

## 功能

- 支持 JWT Bearer Token 鉴权。
- 支持先查询城市标准 ID，再用标准 ID 查询天气。
- 支持类似 `成都市彭州市` 的位置拆分：
  - `location=彭州市`
  - `adm=成都市`
- 支持天气接口：
  - `weather_now`
  - `weather_24h`
  - `weather_3d`
  - `weather_7d`
- 返回 Agent 可理解的结构化数据：
  - `location_info`
  - `weather_data`
  - `source_url`
  - `visualization`
  - `advice`
  - `message`
  - `agent_guide`

## 文件说明

```text
WeatherGet.py        # 天气查询、可视化、建议生成入口
WeatherGetEncode.py  # JWT 生成
WeatherApiPath.py    # 和风天气接口路径字典
.env.example         # 环境变量示例，不包含真实密钥
.gitignore           # 忽略 .env 和缓存文件
```

不要上传真实 `.env` 文件。`ExampleAgent/.gitignore` 已忽略 `.env`。

## 环境变量

复制示例文件：

```powershell
Copy-Item .env.example .env
```

然后填写：

```env
WEATHER_KEY="-----BEGIN PRIVATE KEY-----
YOUR_QWEATHER_ED25519_PRIVATE_KEY
-----END PRIVATE KEY-----"
PROJECT_ID="YOUR_PROJECT_ID"
CREDENTIAL_ID="YOUR_CREDENTIAL_ID"
HOST_API="YOUR_QWEATHER_API_HOST"
```

## 安装依赖

```powershell
pip install requests python-dotenv PyJWT cryptography
```

## 基础调用

```python
from WeatherGet import weather

client = weather(location="成都市彭州市", api_name="weather_3d")
payload = client.get_weather_payload()

print(payload["message"])
```

如果从项目根目录按包导入：

```python
from ExampleAgent.WeatherGet import weather
```

## Agent 可读取的结果

`get_weather_payload()` 会返回一个字典：

```python
{
    "location_info": {...},
    "weather_data": {...},
    "source_url": "https://www.qweather.com/...",
    "visualization": "| 日期 | 白天 | ... |",
    "advice": ["可能有降水，建议带伞..."],
    "message": "可以直接发送给用户的 Markdown 消息",
    "agent_guide": {...},
}
```

其中 `message` 可以直接发给用户，包含：

- Markdown 天气表格或实时天气文本
- 基于天气数据生成的建议
- 和风天气详情链接 `source_url`
- 数据更新时间

## Agent 获取天气数据的流程

1. 解析用户输入位置。
2. 调用城市查询接口：

```text
/geo/v2/city/lookup?location={0}&adm={1}
```

3. 从返回 JSON 中读取：

```python
data["location"][0]["id"]
```

4. 使用标准城市 ID 查询天气，例如：

```text
/v7/weather/3d?location={0}
```

5. 将天气 JSON 转为 Markdown 表格。
6. 从 `fxLink` 取详情 URL。
7. 根据天气文本、温度、降水概率、风力、紫外线生成建议。

## 直接运行

在 `ExampleAgent` 目录中运行：

```powershell
python WeatherGet.py
```

或在项目根目录运行：

```powershell
python ExampleAgent\WeatherGet.py
```

示例输出：

```markdown
## 彭州天气

| 日期 | 白天 | 夜间 | 最高温 | 最低温 | 风向 | 风力 | 紫外线 | 湿度 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-06-02 | 多云 | 阵雨 | 30℃ | 21℃ | 北风 | 1-3级 | 12 | 67% |

### 建议
- 可能有降水，建议带伞，出行注意路面湿滑。
- 气温较高，注意补水、防晒，减少长时间户外暴晒。

详情链接：https://www.qweather.com/weather/pengzhou-101270112.html
更新时间：2026-06-02T09:18+08:00
```

## 上传到 GitHub

只上传 `ExampleAgent` 目录下的文件：

```powershell
git add README.md .gitignore .env.example WeatherGet.py WeatherGetEncode.py WeatherApiPath.py
git commit -m "Add weather agent example"
git push
```
