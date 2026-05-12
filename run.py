"""
run.py
automatically run the route
"""

"""修正坐标误差，百度取点使用 BD-09 坐标系，iOS使用 WGS-09 坐标系，进行转换"""
import math
import time
import random
import asyncio

from geopy.distance import geodesic

from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService

def bd09Towgs84(position):
    wgs_p = {}

    x_pi = 3.14159265358979324 * 3000.0 / 180.0
    pi = 3.141592653589793238462643383  # π
    a = 6378245.0  # 长半轴
    ee = 0.00669342162296594323  # 偏心率平方

    def transform_lat(x, y):
        ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * pi) + 20.0 * math.sin(2.0 * x * pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(y * pi) + 40.0 * math.sin(y / 3.0 * pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(y / 12.0 * pi) + 320 * math.sin(y * pi / 30.0)) * 2.0 / 3.0
        return ret

    def transform_lon(x, y):
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * pi) + 20.0 * math.sin(2.0 * x * pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(x * pi) + 40.0 * math.sin(x / 3.0 * pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(x / 12.0 * pi) + 300.0 * math.sin(x / 30.0 * pi)) * 2.0 / 3.0
        return ret

    x = position['lng'] - 0.0065
    y = position['lat'] - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * x_pi)

    gcj_lng = z * math.cos(theta)
    gcj_lat = z * math.sin(theta)

    d_lat = transform_lat(gcj_lng - 105.0, gcj_lat - 35.0)
    d_lng = transform_lon(gcj_lng - 105.0, gcj_lat - 35.0)

    rad_lat = gcj_lat / 180.0 * pi
    magic = math.sin(rad_lat)
    magic = 1 - ee * magic * magic
    sqrt_magic = math.sqrt(magic)

    d_lng = (d_lng * 180.0) / (a / sqrt_magic * math.cos(rad_lat) * pi)
    d_lat = (d_lat * 180.0) / (a * (1 - ee) / (magic * sqrt_magic) * pi)

    wgs_p["lat"] = gcj_lat * 2 - gcj_lat - d_lat
    wgs_p["lng"] = gcj_lng * 2 - gcj_lng - d_lng
    return wgs_p

# get the ditance according to the latitude and longitude
def geodistance(p1, p2):
    return geodesic((p1["lat"],p1["lng"]),(p2["lat"],p2["lng"])).m

def smooth(start, end, i):
    import math
    i = (i-start)/(end-start)*math.pi
    return math.sin(i)**2

def randLoc(loc: list, d=0.000025, n=5):
    import random
    import time
    import math
    # deepcopy loc
    result = []
    for i in loc:
        result.append(i.copy())

    center = {"lat": 0, "lng": 0}
    for i in result:
        center["lat"] += i["lat"]
        center["lng"] += i["lng"]
    center["lat"] /= len(result)
    center["lng"] /= len(result)
    random.seed(time.time())
    for i in range(n):
        start = int(i*len(result)/n)
        end = int((i+1)*len(result)/n)
        offset = (2*random.random()-1) * d
        for j in range(start, end):
            distance = math.sqrt(
                (result[j]["lat"]-center["lat"])**2 + (result[j]["lng"]-center["lng"])**2
            )
            if 0 == distance:
                continue
            result[j]["lat"] +=  (result[j]["lat"]-center["lat"])/distance*offset*smooth(start, end, j)
            result[j]["lng"] +=  (result[j]["lng"]-center["lng"])/distance*offset*smooth(start, end, j)
    start = int(i*len(result)/n)
    end = len(result)
    offset = (2*random.random()-1) * d
    for j in range(start, end):
        distance = math.sqrt(
            (result[j]["lat"]-center["lat"])**2 + (result[j]["lng"]-center["lng"])**2
        )
        if 0 == distance:
            continue
        result[j]["lat"] +=  (result[j]["lat"]-center["lat"])/distance*offset*smooth(start, end, j)
        result[j]["lng"] +=  (result[j]["lng"]-center["lng"])/distance*offset*smooth(start, end, j)
    return result

def fixLockT(loc: list, v, dt):
    fixedLoc = []
    t = 0
    T = []
    T.append(geodistance(loc[1],loc[0])/v)
    a = loc[0].copy()
    b = loc[1].copy()
    j = 0
    while t < T[0]:
        xa = a["lat"] + j*(b["lat"]-a["lat"])/(max(1, int(T[0]/dt)))
        xb = a["lng"] + j*(b["lng"]-a["lng"])/(max(1, int(T[0]/dt)))
        fixedLoc.append({"lat": xa, "lng": xb})
        j += 1
        t += dt
    for i in range(1, len(loc)):
        T.append(geodistance(loc[(i+1)%len(loc)],loc[i])/v + T[-1])
        a = loc[i].copy()
        b = loc[(i+1)%len(loc)].copy()
        j = 0
        while t < T[i]:
            xa = a["lat"] + j*(b["lat"]-a["lat"])/(max(1, int((T[i]-T[i-1])/dt)))
            xb = a["lng"] + j*(b["lng"]-a["lng"])/(max(1, int((T[i]-T[i-1])/dt)))
            fixedLoc.append({"lat": xa, "lng": xb})
            j += 1
            t += dt
    return fixedLoc

def build_lap_positions(loc: list, v, dt=0.2):
    fixedLoc = fixLockT(loc, v, dt)
    nList = (5, 6, 7, 8, 9)
    n = nList[random.randint(0, len(nList)-1)]
    return randLoc(fixedLoc, n=n)  # a path will be divided into n parts for random route

def replay_positions(simulators, fixedLoc, dt=0.2, stop_event=None):
    clock = time.time()
    for i in fixedLoc:
        if stop_event is not None and stop_event.is_set():
            return False
        point = bd09Towgs84(i)
        for simulator in simulators:
            simulator.set(point["lat"], point["lng"])
        while time.time()-clock < dt:
            if stop_event is not None and stop_event.is_set():
                return False
            time.sleep(0.01)
        clock = time.time()
    return True

async def connect_simulator(endpoint, retries=3, connect_timeout=10):
    udid, address, port = endpoint
    last_error = None
    for attempt in range(1, retries + 1):
        rsd = RemoteServiceDiscoveryService((address, port))
        try:
            await asyncio.wait_for(rsd.connect(), timeout=connect_timeout)
            dvt = DvtSecureSocketProxyService(rsd)
            dvt.perform_handshake()
            simulator = LocationSimulation(dvt)
            print(f"设备 {str(udid)[:8]}... 定位服务连接成功")
            return rsd, simulator
        except Exception as exc:
            last_error = exc
            try:
                await rsd.close()
            except Exception:
                pass
            if attempt < retries:
                print(f"设备 {str(udid)[:8]}... 第 {attempt} 次连接失败，正在重试: {exc}")
                await asyncio.sleep(1)
    raise RuntimeError(f"设备 {str(udid)[:8]}... 无法连接定位服务: {last_error}")

async def run_many(endpoints, loc: list, v, d=15, stop_event=None):
    random.seed(time.time())
    rsds = []
    simulators = []
    try:
        await asyncio.sleep(2)
        for endpoint in endpoints:
            rsd, simulator = await connect_simulator(endpoint)
            rsds.append(rsd)
            simulators.append(simulator)

        # 每次开始运行前先锚定到路线起点，避免从上次中途位置直接跳转
        start_point = bd09Towgs84(loc[0])
        for simulator in simulators:
            simulator.set(start_point["lat"], start_point["lng"])
        await asyncio.sleep(0.2)

        while stop_event is None or not stop_event.is_set():
            vRand = 1000/(1000/v-(2*random.random()-1)*d)
            fixedLoc = build_lap_positions(loc, vRand)
            completed = replay_positions(simulators, fixedLoc, stop_event=stop_event)
            if stop_event is not None and stop_event.is_set():
                break
            if completed:
                print("跑完一圈了")
    finally:
        if simulators:
            try:
                # 停止时先回到起点一次，再停止模拟，减少下次启动时的视觉跳点
                start_point = bd09Towgs84(loc[0])
                for simulator in simulators:
                    simulator.set(start_point["lat"], start_point["lng"])
                await asyncio.sleep(0.2)
                for simulator in simulators:
                    simulator.clear()
            except Exception:
                pass
        for rsd in rsds:
            try:
                await rsd.close()
            except Exception:
                pass

async def run(address, port, loc: list, v, d=15, stop_event=None):
    await run_many([(None, address, port)], loc, v, d=d, stop_event=stop_event)
