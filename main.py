"""项目入口。"""

from __future__ import annotations

import argparse

from src.stage03_app import Stage03App


def main() -> int:
    parser = argparse.ArgumentParser(description="EchoZero Level 1 Vertical Slice")
    parser.add_argument("--smoke-test", action="store_true", help="自动通关正式流程并绘制后退出")
    args = parser.parse_args()
    return Stage03App(smoke_test=args.smoke_test).run()


if __name__ == "__main__":
    raise SystemExit(main())
