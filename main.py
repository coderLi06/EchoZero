"""项目入口。"""

from __future__ import annotations

import argparse

from src.app import GrayboxApp


def main() -> int:
    parser = argparse.ArgumentParser(description="EchoZero Stage 01 灰盒")
    parser.add_argument("--smoke-test", action="store_true", help="绘制一帧后退出")
    args = parser.parse_args()
    return GrayboxApp(smoke_test=args.smoke_test).run()


if __name__ == "__main__":
    raise SystemExit(main())
