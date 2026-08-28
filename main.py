"""项目入口。"""

from __future__ import annotations

import argparse

from src.stage02_app import Stage02App


def main() -> int:
    parser = argparse.ArgumentParser(description="EchoZero Stage02 测试 Encounter")
    parser.add_argument("--smoke-test", action="store_true", help="绘制一帧后退出")
    args = parser.parse_args()
    return Stage02App(smoke_test=args.smoke_test).run()


if __name__ == "__main__":
    raise SystemExit(main())
