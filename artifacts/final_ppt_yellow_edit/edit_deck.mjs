import fs from "node:fs/promises";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const ROOT = "D:/daerxia/程序设计实训/project";
const BUILD = `${ROOT}/artifacts/final_ppt_yellow_edit`;
const OUT = `${BUILD}/EchoZero_终验答辩_4分钟_黄色工业版.pptx`;
const W = 1280;
const H = 720;

const C = {
  bg: "#0B0B09",
  panel: "#1C1B16",
  steel: "#2B2A22",
  steel2: "#5A4B2C",
  paper: "#F2E6C5",
  text: "#F4E7C2",
  muted: "#B1A98F",
  cyan: "#D9A93D",
  amber: "#F0B34A",
  violet: "#C58A32",
  red: "#F06464",
  green: "#9AAE5A",
  black: "#000000",
};

function addRect(slide, name, left, top, width, height, fill, lineFill = "none", lineWidth = 0, radius = false) {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    name,
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: lineFill, width: lineWidth },
    ...(radius ? { borderRadius: "rounded-lg" } : {}),
  });
}

function addText(slide, name, text, left, top, width, height, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    fontSize: options.fontSize ?? 22,
    bold: options.bold ?? false,
    color: options.color ?? C.text,
    alignment: options.alignment ?? "left",
    verticalAlignment: options.verticalAlignment ?? "top",
    fontFamily: options.fontFamily ?? "Microsoft YaHei",
  };
  return shape;
}

async function imageBytes(relPath) {
  const bytes = await fs.readFile(`${ROOT}/${relPath}`);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

async function addImage(slide, name, relPath, left, top, width, height, fit = "cover", radius = false) {
  const blob = await imageBytes(relPath);
  return slide.images.add({
    name,
    blob,
    contentType: relPath.toLowerCase().endsWith(".jpg") ? "image/jpeg" : "image/png",
    alt: `EchoZero 实机截图：${name}`,
    fit,
    position: { left, top, width, height },
    geometry: radius ? "roundRect" : "rect",
    ...(radius ? { borderRadius: "rounded-lg" } : {}),
  });
}

function addHeader(slide, title, section, page) {
  addText(slide, `section-${page}`, section, 56, 34, 300, 24, { fontSize: 16, bold: true, color: C.amber });
  addText(slide, `title-${page}`, title, 56, 64, 1168, 64, { fontSize: 48, bold: true, color: C.text });
  addRect(slide, `rule-${page}`, 56, 139, 1168, 2, C.steel2);
  addText(slide, `page-${page}`, String(page).padStart(2, "0"), 1164, 682, 60, 22, { fontSize: 16, color: C.muted, alignment: "right" });
}

function addNotes(slide, talk, sources) {
  slide.speakerNotes.textFrame.setText(`${talk}\n\n[Sources]\n${sources.map((s) => `- ${s}`).join("\n")}`);
  slide.speakerNotes.setVisible(true);
}

function addMetric(slide, x, value, label, color) {
  addRect(slide, `metric-bg-${x}`, x, 320, 344, 260, C.panel, C.steel2, 2, true);
  addRect(slide, `metric-accent-${x}`, x, 320, 8, 260, color);
  addText(slide, `metric-value-${x}`, value, x + 28, 350, 290, 108, { fontSize: 72, bold: true, color });
  addText(slide, `metric-label-${x}`, label, x + 28, 475, 290, 74, { fontSize: 23, color: C.text });
}

async function main() {
  await fs.mkdir(`${BUILD}/renders`, { recursive: true });
  const deck = Presentation.create({ slideSize: { width: W, height: H } });

  // 1. Cover — Codex Grid slide-08 hierarchy: title/body on left, strong image field on right.
  {
    const s = deck.slides.add();
    s.background.fill = C.bg;
    await addImage(s, "cover-boss", "artifacts/final_ppt_yellow_edit/artifacts/meowa_ui_qa/06_boss_1280x800.png", 610, 0, 670, 720, "cover", false);
    addRect(s, "cover-image-divider", 604, 0, 6, 720, C.amber);
    addRect(s, "cover-left-field", 0, 0, 610, 720, C.bg);
    addText(s, "cover-kicker", "PYTHON · PYGAME-CE · 8 DAYS", 58, 66, 470, 28, { fontSize: 18, bold: true, color: C.amber });
    addText(s, "cover-title-en", "ECHO // ZERO", 58, 138, 490, 82, { fontSize: 72, bold: true, color: C.text, fontFamily: "Bahnschrift" });
    addText(s, "cover-title-cn", "冻结战局，改写因果", 58, 242, 490, 62, { fontSize: 44, bold: true, color: C.cyan });
    addText(s, "cover-sub", "动作 Roguelike × 三拍战术因果编排\n两个完整关卡 · 可解释 AI · 可复现验证", 58, 348, 476, 116, { fontSize: 27, color: C.text });
    addRect(s, "cover-proof-rule", 58, 520, 460, 2, C.steel2);
    addText(s, "cover-proof", "终验答辩｜核心创新可见、技术可解释、现场可演示", 58, 548, 474, 62, { fontSize: 20, color: C.muted });
    addText(s, "cover-date", "2026.09", 58, 658, 150, 22, { fontSize: 16, color: C.muted });
    addNotes(s, "约 25 秒。开场只讲一句：EchoZero 是实时动作 Roguelike，但在危险瞬间可以冻结战局，用三拍顺序改写结果。随后说明今天用四分钟证明：它可玩、创新清楚、技术可信。", [
      `${ROOT}/项目配置.md`,
      `${ROOT}/INNOVATION.md`,
      `${ROOT}/artifacts/final_ppt_yellow_edit/artifacts/meowa_ui_qa/06_boss_1280x800.png`,
    ]);
  }

  // 2. Complete playable loop.
  {
    const s = deck.slides.add();
    s.background.fill = C.bg;
    addHeader(s, "不是概念原型，而是一局完整的动作 Roguelike", "01 / 功能与界面", 2);
    await addImage(s, "action-loop", "artifacts/final_ppt_yellow_edit/artifacts/meowa_ui_qa/02_action_1280x800.png", 506, 174, 718, 404, "cover", true);
    const steps = [
      ["01", "实时交锋", "WASD、近/远程、闪避、牵引", C.amber],
      ["02", "冻结危险瞬间", "读取 Enemy Intent，进入三拍 Tactical", C.cyan],
      ["03", "三选一成长", "协议 / 技能 / 属性改变后续战斗", C.violet],
      ["04", "完整 Run", "程序地图 → 3 个遭遇 → 12 HP Boss", C.green],
    ];
    let y = 174;
    for (const [n, title, body, color] of steps) {
      addText(s, `loop-num-${n}`, n, 58, y, 52, 34, { fontSize: 22, bold: true, color });
      addText(s, `loop-title-${n}`, title, 124, y - 2, 310, 34, { fontSize: 27, bold: true, color: C.text });
      addText(s, `loop-body-${n}`, body, 124, y + 38, 330, 46, { fontSize: 20, color: C.muted });
      addRect(s, `loop-rule-${n}`, 58, y + 94, 398, 1, C.steel2);
      y += 106;
    }
    addText(s, "loop-ui-caption", "实机：中文 HUD、敌我编号、Intent 倒计时、构筑常驻显示", 506, 594, 718, 34, { fontSize: 20, color: C.muted });
    addText(s, "loop-summary", "60% 动作 · 25% 策略 · 15% Build", 58, 620, 398, 44, { fontSize: 26, bold: true, color: C.amber });
    addNotes(s, "约 35 秒。按左侧四步讲完整循环，画面只指三个信息：敌人意图、冷却与构筑。强调正式入口不是单场演示：有程序地图、奖励、三场遭遇和 Boss 终局。", [
      `${ROOT}/README.md`,
      `${ROOT}/项目配置.md`,
      `${ROOT}/artifacts/final_ppt_yellow_edit/artifacts/meowa_ui_qa/02_action_1280x800.png`,
    ]);
  }

  // 3. Core innovation — paired evidence inspired by slide-10.
  {
    const s = deck.slides.add();
    s.background.fill = C.bg;
    addHeader(s, "同样三招，只换顺序，失败就变成击杀", "02 / 主创新：三拍命令链 + 因果预演", 3);
    await addImage(s, "tactical-pool", "artifacts/final_ppt_yellow_edit/artifacts/meowa_ui_qa/03_tactical_1280x800.png", 56, 176, 522, 326, "cover", true);
    await addImage(s, "causality-rewritten", "logs/visual_polish/11_causality_rewritten.png", 702, 176, 522, 326, "cover", true);
    addText(s, "before-label", "原顺序：推击 → 移动 → 牵引", 74, 518, 490, 34, { fontSize: 24, bold: true, color: C.red });
    addText(s, "before-desc", "敌人存活，锁定意图继续结算", 74, 558, 490, 34, { fontSize: 20, color: C.muted });
    addText(s, "arrow", "→", 598, 298, 84, 84, { fontSize: 64, bold: true, color: C.amber, alignment: "center" });
    addText(s, "after-label", "新顺序：牵引 → 推击 → 移动", 720, 518, 490, 34, { fontSize: 24, bold: true, color: C.cyan });
    addText(s, "after-desc", "敌人在行动前死亡，意图自动取消", 720, 558, 490, 34, { fontSize: 20, color: C.muted });
    addRect(s, "innovation-band", 56, 622, 1168, 50, C.panel, C.steel2, 1, true);
    addText(s, "innovation-band-text", "Preview 不是录制动画：状态副本与真实 Execute 调用同一个 simulate_turn", 82, 634, 1116, 28, { fontSize: 22, bold: true, color: C.amber, alignment: "center" });
    addNotes(s, "约 40 秒。这一页是答辩的核心。先讲敌人意图固定，再读左右两种顺序。重点落在：画面预测和真实执行共用同一个模拟器，所以玩家看到的因果就是之后发生的结果。", [
      `${ROOT}/INNOVATION.md`,
      `${ROOT}/ARCHITECTURE.md`,
      `${ROOT}/artifacts/final_ppt_yellow_edit/artifacts/meowa_ui_qa/03_tactical_1280x800.png`,
      `${ROOT}/logs/visual_polish/11_causality_rewritten.png`,
    ]);
  }

  // 4. Two levels and Builds.
  {
    const s = deck.slides.add();
    s.background.fill = C.bg;
    addHeader(s, "第二关不加一套系统，而是反转玩家已学会的规则", "03 / 两关差异与构筑深度", 4);
    await addImage(s, "level1-stable", "logs/visual_polish/12_level1_1920x1080.png", 56, 172, 548, 305, "cover", true);
    await addImage(s, "level2-reverse", "logs/visual_polish/09_level2_reverse.png", 676, 172, 548, 305, "cover", true);
    addText(s, "level1-title", "Level 1｜校准舱：稳定 1→2→3", 72, 492, 520, 34, { fontSize: 24, bold: true, color: C.cyan });
    addText(s, "level1-body", "教学换序、首次协议、三遭遇闭环", 72, 532, 520, 34, { fontSize: 20, color: C.muted });
    addText(s, "level2-title", "Level 2｜逆相反应堆：3→2→1", 692, 492, 520, 34, { fontSize: 24, bold: true, color: C.violet });
    addText(s, "level2-body", "相位锚锁相、多格 Intent、守卫终局", 692, 532, 520, 34, { fontSize: 20, color: C.muted });
    const builds = [
      ["回声编排", "奖励空拍：首拍在第三拍重放", C.cyan],
      ["动能破阵", "奖励墙面：推击 + 碰撞过载", C.amber],
      ["屏障反推", "奖励顺序：先盾后推才增伤", C.green],
    ];
    let x = 56;
    for (const [title, body, color] of builds) {
      addRect(s, `build-${title}`, x, 602, 358, 72, C.panel, color, 2, true);
      addText(s, `build-title-${title}`, title, x + 18, 612, 120, 28, { fontSize: 21, bold: true, color });
      addText(s, `build-body-${title}`, body, x + 142, 611, 196, 46, { fontSize: 17, color: C.text });
      x += 405;
    }
    addNotes(s, "约 35 秒。第一关教稳定顺序，第二关把同一时间轴改为逆序，并用相位锚把空间位置和时间规则绑定。最后用三条 Build 说明成长不是三档攻击力，而是分别奖励空拍、墙面和先后顺序。", [
      `${ROOT}/项目配置.md`,
      `${ROOT}/INNOVATION.md`,
      `${ROOT}/DEMO_PLAN.md`,
      `${ROOT}/logs/visual_polish/12_level1_1920x1080.png`,
      `${ROOT}/logs/visual_polish/09_level2_reverse.png`,
    ]);
  }

  // 5. Technical credibility.
  {
    const s = deck.slides.add();
    s.background.fill = C.bg;
    addHeader(s, "三条技术线共同保证：可解释、可复现、不穿帮", "04 / 技术实现", 5);
    await addImage(s, "debug-panel", "artifacts/final_ppt_yellow_edit/artifacts/meowa_ui_qa/09_debug_1280x800.png", 720, 174, 504, 390, "cover", true);
    const rows = [
      ["确定性模拟", "clone(state) → simulate_turn → fingerprint", "Preview = Execute 终态", C.cyan],
      ["程序地图", "Seed → 房间/走廊 → BFS → 距离校验", "同 Seed 复现，非法则重试", C.green],
      ["行为树 AI", "Selector / Sequence → PreparedAction", "同一 Action 驱动 Intent 与执行", C.amber],
    ];
    let y = 184;
    for (const [title, flow, outcome, color] of rows) {
      addRect(s, `tech-node-${title}`, 56, y, 612, 118, C.panel, color, 2, true);
      addText(s, `tech-title-${title}`, title, 78, y + 16, 164, 32, { fontSize: 24, bold: true, color });
      addText(s, `tech-flow-${title}`, flow, 244, y + 14, 398, 34, { fontSize: 20, bold: true, color: C.text, fontFamily: "Consolas" });
      addText(s, `tech-outcome-${title}`, outcome, 244, y + 61, 398, 32, { fontSize: 18, color: C.muted });
      y += 136;
    }
    addRect(s, "tech-boundary", 56, 624, 1168, 46, C.steel, C.steel2, 1, true);
    addText(s, "tech-boundary-text", "领域层不导入 pygame；动画与音效只消费 LogicEvent，不改变伤害、位置或胜负", 76, 635, 1128, 24, { fontSize: 20, bold: true, color: C.text, alignment: "center" });
    addText(s, "debug-caption", "F3 面板只在答辩展示；正式 HUD 隐藏内部实现", 720, 580, 504, 28, { fontSize: 18, color: C.muted });
    addNotes(s, "约 40 秒。只讲三条线：预演同源、地图可复现、AI 可解释。右图可指 F3 面板中的 Selector/Sequence/Condition。最后用底部一句交代领域与表现分离，避免动画改逻辑。", [
      `${ROOT}/ARCHITECTURE.md`,
      `${ROOT}/功能测试与初验报告.md`,
      `${ROOT}/artifacts/final_ppt_yellow_edit/artifacts/meowa_ui_qa/09_debug_1280x800.png`,
    ]);
  }

  // 6. AI collaboration — dedicated required slide.
  {
    const s = deck.slides.add();
    s.background.fill = C.bg;
    addHeader(s, "AI 提高迭代速度，人负责证据、边界与最终判断", "05 / AI 协作（独立评分项）", 6);
    const process = ["冻结需求", "AI 方案/代码/测试", "真人运行审图", "反证与取舍", "回归并归档"];
    let x = 56;
    for (let i = 0; i < process.length; i++) {
      addRect(s, `ai-step-${i}`, x, 170, 196, 58, i === 3 ? C.steel : C.panel, i === 3 ? C.amber : C.steel2, 2, true);
      addText(s, `ai-step-text-${i}`, process[i], x + 10, 184, 176, 28, { fontSize: 20, bold: true, color: i === 3 ? C.amber : C.text, alignment: "center" });
      if (i < process.length - 1) addText(s, `ai-arrow-${i}`, "→", x + 199, 183, 34, 28, { fontSize: 24, bold: true, color: C.muted, alignment: "center" });
      x += 235;
    }
    await addImage(s, "ai-before", "artifacts/ui_polish_pass1/03_tactical_1280x800.png", 56, 266, 356, 222, "cover", true);
    await addImage(s, "ai-after", "artifacts/final_ppt_yellow_edit/artifacts/meowa_ui_qa/03_tactical_1280x800.png", 438, 266, 356, 222, "cover", true);
    addText(s, "ai-before-label", "首轮：扫描过强 / 构筑区偏空", 64, 500, 340, 28, { fontSize: 18, color: C.red, alignment: "center" });
    addText(s, "ai-after-label", "回修：单扫描线 / 增长信息补齐", 446, 500, 340, 28, { fontSize: 18, color: C.green, alignment: "center" });
    addText(s, "ai-critical-title", "三个关键的人类判断", 842, 266, 382, 34, { fontSize: 26, bold: true, color: C.amber });
    const decisions = [
      "否决“另写预演规则”\n→ Preview / Execute 统一 simulate_turn",
      "不相信“代码改完即完成”\n→ 六状态截图审查后再 Smoke",
      "盲测数值意见相互矛盾\n→ 不冒险改平衡，只修共性可读性",
    ];
    let dy = 318;
    for (let i = 0; i < decisions.length; i++) {
      addRect(s, `decision-mark-${i}`, 842, dy + 5, 8, 70, i === 0 ? C.cyan : i === 1 ? C.violet : C.green);
      addText(s, `decision-${i}`, decisions[i], 864, dy, 350, 78, { fontSize: 19, color: C.text });
      dy += 92;
    }
    addRect(s, "ai-roles", 56, 570, 1168, 88, C.panel, C.steel2, 1, true);
    addText(s, "ai-role-ai", "AI：方案比较、代码辅助、测试生成、视觉审查、文档整理", 78, 586, 530, 50, { fontSize: 20, color: C.cyan });
    addText(s, "ai-role-human", "人：冻结方向、运行验证、版权/风险把关、否决错误、现场验收", 640, 586, 560, 50, { fontSize: 20, color: C.amber });
    addNotes(s, "约 45 秒。本页必须独立讲。先说协作闭环，再用前后截图证明不是一次生成即交付。三个例子依次对应：架构边界、运行画面验证、面对冲突证据时不盲改。最后明确人机分工。", [
      `${ROOT}/项目配置.md`,
      `${ROOT}/AGENTS.md`,
      `${ROOT}/每日工作日志.md`,
      `${ROOT}/TASKS.md`,
      `${ROOT}/docs/blind-tests/盲测汇总.md`,
      `${ROOT}/artifacts/ui_polish_pass1/03_tactical_1280x800.png`,
      `${ROOT}/artifacts/final_ppt_yellow_edit/artifacts/meowa_ui_qa/03_tactical_1280x800.png`,
    ]);
  }

  // 7. Acceptance proof — metric-led slide-19 reference.
  {
    const s = deck.slides.add();
    s.background.fill = C.bg;
    addHeader(s, "终验结论：创新可见、流程跑通、交付可复现", "06 / 验收证据", 7);
    addText(s, "evidence-lead", "项目证据覆盖自动化、完整路径、真人盲测与发布包，而不是只展示代码截图。", 56, 166, 1168, 48, { fontSize: 25, color: C.text });
    addMetric(s, 56, "131", "项自动化测试全部通过\n覆盖模拟、AI、地图、UI 与双关", C.cyan);
    addMetric(s, 468, "100%", "3/3 新玩家理解 Preview 与 Reverse", C.green);
    addMetric(s, 880, "2/3", "新玩家无指导通关\n观察者介入 0/3、无阻断问题", C.amber);
    addRect(s, "delivery-strip", 56, 610, 1168, 62, C.steel, C.steel2, 1, true);
    addText(s, "delivery-text", "PyInstaller onedir 已交付 · Action / Showcase 两条发布版 Smoke 退出码 0 · 固定 Seed 可复现演示", 76, 627, 1128, 28, { fontSize: 21, bold: true, color: C.text, alignment: "center" });
    addText(s, "close-line", "现在请看现场演示：同样三招，顺序如何改写结局。", 56, 254, 1168, 42, { fontSize: 31, bold: true, color: C.violet, alignment: "center" });
    addNotes(s, "约 30 秒。用三个数字收口：131 项测试、Preview/Reverse 理解 100%、2/3 通关且无人介入。补一句发布包和两条 Smoke 已通过，然后不要说谢谢，直接转入现场演示。总讲解约 4 分钟。", [
      `${ROOT}/功能测试与初验报告.md`,
      `${ROOT}/docs/blind-tests/盲测汇总.md`,
      `${ROOT}/答辩预评分报告.md`,
    ]);
  }

  for (const [index, slide] of deck.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    const png = await deck.export({ slide, format: "png", scale: 1 });
    await fs.writeFile(`${BUILD}/renders/${stem}.png`, new Uint8Array(await png.arrayBuffer()));
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(`${BUILD}/renders/${stem}.layout.json`, await layout.text());
  }
  const montage = await deck.export({ format: "webp", montage: true, scale: 1 });
  await fs.writeFile(`${BUILD}/renders/deck-montage.webp`, new Uint8Array(await montage.arrayBuffer()));
  const pptx = await PresentationFile.exportPptx(deck);
  await pptx.save(OUT);
  console.log(OUT);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
