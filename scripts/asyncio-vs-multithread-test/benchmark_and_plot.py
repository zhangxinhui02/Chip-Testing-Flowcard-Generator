import asyncio
import csv
import statistics
import time
from pathlib import Path

import httpx
import matplotlib.pyplot as plt
import psutil


SERVERS = {
    "FastAPI Async": {
        "url": "http://127.0.0.1:8000/io",
        "health": "http://127.0.0.1:8000/health",
        "port": 8000,
    },
    "ThreadPool HTTP": {
        "url": "http://127.0.0.1:8001/io",
        "health": "http://127.0.0.1:8001/health",
        "port": 8001,
    },
}

TOTAL_REQUESTS = 2000

CONCURRENCY_LEVELS = [10, 50, 100, 200, 500, 1000]

IO_DELAY = 0.1

OUTPUT_DIR = Path("benchmark_results")
OUTPUT_DIR.mkdir(exist_ok=True)


def find_process_by_listen_port(port: int):
    """
    根据监听端口查找服务端进程。

    注意：
    - 在 Linux/macOS/Windows 上通常可用；
    - 如果权限不足，可能无法读取部分进程连接信息；
    - 建议以当前用户启动服务端和压测程序。
    """
    for conn in psutil.net_connections(kind="inet"):
        try:
            if (
                    conn.status == psutil.CONN_LISTEN
                    and conn.laddr
                    and conn.laddr.port == port
                    and conn.pid is not None
            ):
                return psutil.Process(conn.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return None


async def check_server(name: str, health_url: str):
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(health_url)
            resp.raise_for_status()
        print(f"[OK] {name} is ready.")
    except Exception as e:
        raise RuntimeError(f"{name} is not ready: {health_url}, error={e}") from e


class ResourceMonitor:
    """
    采集单个进程的资源使用情况。

    采集指标：
    - RSS 内存占用；
    - CPU 使用率；
    - 线程数量。
    """

    def __init__(self, process: psutil.Process, interval: float = 0.1):
        self.process = process
        self.interval = interval
        self.running = False
        self.samples = []

    async def start(self):
        self.running = True

        # 初始化 CPU 统计，否则第一次 cpu_percent 可能不准确
        try:
            self.process.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return

        while self.running:
            try:
                memory_info = self.process.memory_info()
                cpu_percent = self.process.cpu_percent(interval=None)
                thread_count = self.process.num_threads()

                self.samples.append({
                    "timestamp": time.perf_counter(),
                    "rss_mb": memory_info.rss / 1024 / 1024,
                    "cpu_percent": cpu_percent,
                    "thread_count": thread_count,
                })

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break

            await asyncio.sleep(self.interval)

    def stop(self):
        self.running = False

    def summary(self):
        if not self.samples:
            return {
                "avg_rss_mb": 0,
                "max_rss_mb": 0,
                "avg_cpu_percent": 0,
                "max_cpu_percent": 0,
                "avg_thread_count": 0,
                "max_thread_count": 0,
            }

        rss_values = [s["rss_mb"] for s in self.samples]
        cpu_values = [s["cpu_percent"] for s in self.samples]
        thread_values = [s["thread_count"] for s in self.samples]

        return {
            "avg_rss_mb": statistics.mean(rss_values),
            "max_rss_mb": max(rss_values),
            "avg_cpu_percent": statistics.mean(cpu_values),
            "max_cpu_percent": max(cpu_values),
            "avg_thread_count": statistics.mean(thread_values),
            "max_thread_count": max(thread_values),
        }


async def single_request(client: httpx.AsyncClient, url: str, delay: float):
    start = time.perf_counter()

    try:
        resp = await client.get(url, params={"delay": delay})
        elapsed = time.perf_counter() - start

        return {
            "success": resp.status_code == 200,
            "latency": elapsed,
            "status_code": resp.status_code,
        }

    except Exception:
        elapsed = time.perf_counter() - start

        return {
            "success": False,
            "latency": elapsed,
            "status_code": None,
        }


async def run_benchmark_for_server(
        server_name: str,
        url: str,
        process: psutil.Process | None,
        concurrency: int,
        total_requests: int,
        delay: float,
):
    semaphore = asyncio.Semaphore(concurrency)

    timeout = httpx.Timeout(
        connect=10.0,
        read=60.0,
        write=10.0,
        pool=60.0,
    )

    limits = httpx.Limits(
        max_connections=concurrency + 50,
        max_keepalive_connections=concurrency + 50,
    )

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        async def bounded_request():
            async with semaphore:
                return await single_request(client, url, delay)

        # 预热，降低首次连接、缓存、解释器调度等偶然因素影响
        warmup_count = min(100, total_requests)
        warmup_tasks = [bounded_request() for _ in range(warmup_count)]
        await asyncio.gather(*warmup_tasks)

        monitor = None
        monitor_task = None

        if process is not None:
            monitor = ResourceMonitor(process)
            monitor_task = asyncio.create_task(monitor.start())

            # 给监控器一个采样起点
            await asyncio.sleep(0.2)

        start_time = time.perf_counter()

        tasks = [bounded_request() for _ in range(total_requests)]
        results = await asyncio.gather(*tasks)

        total_time = time.perf_counter() - start_time

        if monitor is not None:
            monitor.stop()

        if monitor_task is not None:
            await monitor_task

    success_results = [r for r in results if r["success"]]
    failed_count = len(results) - len(success_results)
    latencies = [r["latency"] for r in success_results]

    if latencies:
        latencies_sorted = sorted(latencies)

        def percentile(p: float):
            index = int(len(latencies_sorted) * p)
            index = min(index, len(latencies_sorted) - 1)
            return latencies_sorted[index]

        avg_latency_ms = statistics.mean(latencies) * 1000
        p50_latency_ms = percentile(0.50) * 1000
        p95_latency_ms = percentile(0.95) * 1000
        p99_latency_ms = percentile(0.99) * 1000
        rps = len(success_results) / total_time
    else:
        avg_latency_ms = 0
        p50_latency_ms = 0
        p95_latency_ms = 0
        p99_latency_ms = 0
        rps = 0

    if monitor is not None:
        resource_summary = monitor.summary()
    else:
        resource_summary = {
            "avg_rss_mb": 0,
            "max_rss_mb": 0,
            "avg_cpu_percent": 0,
            "max_cpu_percent": 0,
            "avg_thread_count": 0,
            "max_thread_count": 0,
        }

    return {
        "server": server_name,
        "concurrency": concurrency,
        "total_requests": total_requests,
        "success_requests": len(success_results),
        "failed_requests": failed_count,
        "total_time": total_time,
        "rps": rps,
        "avg_latency_ms": avg_latency_ms,
        "p50_latency_ms": p50_latency_ms,
        "p95_latency_ms": p95_latency_ms,
        "p99_latency_ms": p99_latency_ms,
        **resource_summary,
    }


async def run_all_benchmarks():
    for name, info in SERVERS.items():
        await check_server(name, info["health"])

    process_map = {}

    for name, info in SERVERS.items():
        process = find_process_by_listen_port(info["port"])
        process_map[name] = process

        if process is None:
            print(f"[WARN] Cannot find process for {name} on port {info['port']}.")
        else:
            print(
                f"[OK] {name} process found: "
                f"pid={process.pid}, name={process.name()}"
            )

    all_results = []

    for concurrency in CONCURRENCY_LEVELS:
        for server_name, info in SERVERS.items():
            print(
                f"Benchmarking {server_name}, "
                f"concurrency={concurrency}, "
                f"requests={TOTAL_REQUESTS}, "
                f"delay={IO_DELAY}s"
            )

            result = await run_benchmark_for_server(
                server_name=server_name,
                url=info["url"],
                process=process_map[server_name],
                concurrency=concurrency,
                total_requests=TOTAL_REQUESTS,
                delay=IO_DELAY,
            )

            all_results.append(result)

            print(
                f"  RPS={result['rps']:.2f}, "
                f"AVG={result['avg_latency_ms']:.2f}ms, "
                f"P95={result['p95_latency_ms']:.2f}ms, "
                f"P99={result['p99_latency_ms']:.2f}ms, "
                f"FAILED={result['failed_requests']}, "
                f"MAX_MEM={result['max_rss_mb']:.2f}MB, "
                f"MAX_THREADS={result['max_thread_count']}"
            )

    return all_results


def save_csv(results, path: Path):
    fieldnames = [
        "server",
        "concurrency",
        "total_requests",
        "success_requests",
        "failed_requests",
        "total_time",
        "rps",
        "avg_latency_ms",
        "p50_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "avg_rss_mb",
        "max_rss_mb",
        "avg_cpu_percent",
        "max_cpu_percent",
        "avg_thread_count",
        "max_thread_count",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def plot_metric(results, metric: str, ylabel: str, title: str, output_path: Path):
    plt.figure(figsize=(10, 6))

    for server_name in SERVERS.keys():
        server_results = [
            r for r in results
            if r["server"] == server_name
        ]
        server_results.sort(key=lambda x: x["concurrency"])

        x = [r["concurrency"] for r in server_results]
        y = [r[metric] for r in server_results]

        plt.plot(x, y, marker="o", label=server_name)

    plt.xlabel("Concurrency")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_all(results):
    plot_metric(
        results,
        metric="rps",
        ylabel="Requests Per Second",
        title="Throughput Comparison",
        output_path=OUTPUT_DIR / "throughput_comparison.png",
    )

    plot_metric(
        results,
        metric="avg_latency_ms",
        ylabel="Average Latency / ms",
        title="Average Latency Comparison",
        output_path=OUTPUT_DIR / "avg_latency_comparison.png",
    )

    plot_metric(
        results,
        metric="p95_latency_ms",
        ylabel="P95 Latency / ms",
        title="P95 Latency Comparison",
        output_path=OUTPUT_DIR / "p95_latency_comparison.png",
    )

    plot_metric(
        results,
        metric="p99_latency_ms",
        ylabel="P99 Latency / ms",
        title="P99 Latency Comparison",
        output_path=OUTPUT_DIR / "p99_latency_comparison.png",
    )

    plot_metric(
        results,
        metric="failed_requests",
        ylabel="Failed Requests",
        title="Failed Requests Comparison",
        output_path=OUTPUT_DIR / "failed_requests_comparison.png",
    )

    plot_metric(
        results,
        metric="max_rss_mb",
        ylabel="Max RSS Memory / MB",
        title="Max Memory Usage Comparison",
        output_path=OUTPUT_DIR / "max_memory_comparison.png",
    )

    plot_metric(
        results,
        metric="max_cpu_percent",
        ylabel="Max CPU Percent",
        title="Max CPU Usage Comparison",
        output_path=OUTPUT_DIR / "max_cpu_comparison.png",
    )

    plot_metric(
        results,
        metric="max_thread_count",
        ylabel="Max Thread Count",
        title="Max Thread Count Comparison",
        output_path=OUTPUT_DIR / "max_thread_count_comparison.png",
    )


def main():
    results = asyncio.run(run_all_benchmarks())

    csv_path = OUTPUT_DIR / "benchmark_results.csv"
    save_csv(results, csv_path)
    plot_all(results)

    print()
    print(f"CSV result saved to: {csv_path}")
    print(f"Charts saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
