"""项目入口。"""

from __future__ import annotations

import argparse

from src.action_app import ActionApp
from src.stage03_app import Stage03App


def main() -> int:
    parser = argparse.ArgumentParser(description="EchoZero action Roguelike")
    parser.add_argument("--smoke-test", action="store_true", help="自动走通程序 Run 并绘制后退出")
    parser.add_argument("--showcase", action="store_true", help="启动原双关卡 Tactical Showcase")
    parser.add_argument("--showcase-smoke-test", action="store_true", help="自动走通原双关卡 Showcase")
    parser.add_argument("--seed", type=int, help="调试：使用固定 Run Seed")
    args = parser.parse_args()
    if args.showcase or args.showcase_smoke_test:
        return Stage03App(
            smoke_test=args.showcase_smoke_test,
            seed=args.seed,
            random_rewards=args.seed is None and not args.showcase_smoke_test,
        ).run()
    app = ActionApp(smoke_test=args.smoke_test, seed=args.seed)
    result = app.run()
    if result == 0 and app.launch_showcase:
        return Stage03App(random_rewards=True).run()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
