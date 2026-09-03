import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";
const ROOT="D:/daerxia/程序设计实训/project";
const DIR=`${ROOT}/artifacts/final_ppt_outlook_edit`;
const INPUT=`${DIR}/source_current.pptx`;
const OUTPUT=`${DIR}/EchoZero_终验答辩.pptx`;
const deck=await PresentationFile.importPptx(await FileBlob.load(INPUT));
function shape(slide,name){const found=slide.shapes.items.find((x)=>x.name===name); if(!found) throw new Error(`Missing shape: ${name}`); return found;}
function setText(slide,name,value){shape(slide,name).text=value;}
function setNotes(slide,talk,sources){slide.speakerNotes.textFrame.setText(`${talk}\n\n[Sources]\n${sources.map((s)=>`- ${s}`).join("\n")}`); slide.speakerNotes.setVisible(true);}
const sourceChallenge=deck.slides.items[7];
const sourceSummary=deck.slides.items[8];
const challenge=sourceChallenge.duplicate();
challenge.moveTo(deck.slides.items.length-1);
setText(challenge,"section-10","09 / 实现难点与解决");
setText(challenge,"title-10","AI 加速技术实现，玩法与视觉仍要人来判断");
setText(challenge,"page-10","12");
const oldCases=["案例 1｜预演会不会“骗玩家”","案例 2｜画面是否真的清楚","案例 3｜是不是代码 Bug"];
const cases=[
  ["难点 1｜玩法是否真正好玩","快速实现操作、规则和敌人行为","不能亲自感受节奏、压力和策略是否有趣","开发者反复试玩，删掉不明显或不好玩的设计"],
  ["难点 2｜难度和数值是否合适","生成测试、统计结果并快速修改参数","无法可靠判断玩家觉得太难、太简单还是不公平","3 名新玩家无提示盲测；意见不一致时不盲改数值"],
  ["难点 3｜UI 风格和细节不及预期","快速完成界面结构和信息显示","初版容易普通，风格统一和细节质感不足","ui-ux-pro-max 梳理规则，Meowa 统一素材，Figma 反复审图"],
];
for(let i=0;i<3;i++){
  const old=oldCases[i]; const [title,ai,limit,solution]=cases[i];
  setText(challenge,`case-title-${old}`,title);
  setText(challenge,`case-ai-${old}`,ai);
  setText(challenge,`case-check-${old}`,limit);
  setText(challenge,`case-decision-${old}`,solution);
  setText(challenge,`case-labels-${old}`,"AI 擅长");
  setText(challenge,`case-labelh-${old}`,"AI 局限");
  setText(challenge,`case-labeld-${old}`,"解决方法");
}
setText(challenge,"ai-boundary-text","结论：AI 负责加速技术实现；开发者与真实玩家决定玩法、难度、数值和最终视觉质量。");
setNotes(challenge,"这一页如实说明项目中的难点。AI 在写代码、补测试和排查问题上很快，但不能代替真实游戏体验。玩法与数值由开发者试玩和真人盲测决定；界面则借助 ui-ux-pro-max、Meowa 与 Figma 多轮升级。",[
 `${ROOT}/TASKS.md`,`${ROOT}/每日工作日志.md`,`${ROOT}/docs/blind-tests/盲测汇总.md`,`${ROOT}/docs/FIGMA_ASEPRITE_UPGRADE.md`,`${ROOT}/docs/FIGMA_MOTION_AUDIT.md`
]);
const summary=sourceSummary.duplicate();
summary.moveTo(deck.slides.items.length-1);
setText(summary,"section-11","10 / 总结与展望");
setText(summary,"title-11","先把核心玩法做深，再用更多测试把数值调准");
setText(summary,"page-11","13");
setText(summary,"evidence-lead","EchoZero 已完成可玩的双关 Demo；下一阶段不盲目增加内容，而是继续强化三拍因果编排。");
setText(summary,"close-line","当前总结：核心循环已跑通，创新能被理解，项目可以稳定演示。");
setText(summary,"metric-value-56","玩法");
setText(summary,"metric-label-56","增加三拍动作之间的连锁\n让换序产生更多有意义的结果");
setText(summary,"metric-value-468","关卡");
setText(summary,"metric-label-468","增加围绕顺序、地形和敌人组合的变化\n不只是增加敌人数量");
setText(summary,"metric-value-880","平衡");
setText(summary,"metric-label-880","记录通关率、受伤、选择和失败位置\n用多轮盲测调整数值");
setText(summary,"delivery-text","后续优先级：核心玩法深度 → 新手可读性 → 数值平衡 → 内容数量");
setNotes(summary,"总结时先肯定当前结果：完整循环、两关、主创新和稳定演示都已经完成。展望只讲两个重点：继续丰富核心玩法，并通过更多真人盲测调整难度与数值平衡。",[
 `${ROOT}/项目配置.md`,`${ROOT}/ROADMAP.md`,`${ROOT}/INNOVATION.md`,"用户本轮提供的展望方向"
]);
await fs.mkdir(`${DIR}/renders`,{recursive:true});
for(const [i,s] of deck.slides.items.entries()){
 const n=String(i+1).padStart(2,"0");
 const png=await deck.export({slide:s,format:"png",scale:1});
 await fs.writeFile(`${DIR}/renders/slide-${n}.png`,new Uint8Array(await png.arrayBuffer()));
 const layout=await s.export({format:"layout"});
 await fs.writeFile(`${DIR}/renders/slide-${n}.layout.json`,await layout.text());
}
const montage=await deck.export({format:"webp",montage:true,scale:1});
await fs.writeFile(`${DIR}/renders/montage.webp`,new Uint8Array(await montage.arrayBuffer()));
const inspect=await deck.inspect({kind:"slide,textbox,shape,image,notes,layout",maxChars:250000});
await fs.writeFile(`${DIR}/final-inspect.ndjson`,inspect.ndjson);
const pptx=await PresentationFile.exportPptx(deck);
await pptx.save(OUTPUT);
console.log(`slides=${deck.slides.items.length}`);
console.log(OUTPUT);