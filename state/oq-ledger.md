# 待确认项台账（持久）

**这个文件是跨报告长期有效的。** 同一本文献、同一个术语、同一条导师拍过的口径，登记一次之后**不再重复问用户**。

## 读写协议（每次第二轮审查都必须执行）

1. **先读**：对本次出现的每个"拿不准"的概念/术语/口径，先在本台账里查——
   - 命中且 `状态 = resolved` → **直接采用 `答案` 列**，当场消解，**不再报为待确认项**，也不许再问用户。
   - 命中且 `状态 = answered` → 采用答案，并在报告里注明"依已于 `<日期>` 确认的口径"。
   - 命中且 `状态 = open` → 报告里**引用其 OQ-ID**，不重复登记、不重复提问（可在收尾清单里提一句"仍等待确认"）。
   - **未命中** → 在报告里标 `<待确认:…>`，并**在本台账追加一行 `open`**。
2. **去重键**：字典/术语按 `概念`；跨文献的通用口径按 `类型 + 问题`。**同概念只允许一行**，新的出处追加到同一行的 `出处` 列，不新开行。
3. **人工填写**：任何人（包括用户）可随时把 `open` 行的 `答案` 填上、`状态` 改为 `resolved`；下次运行自动消解。
4. **不在报告正文里硬编码台账答案的推理过程**：正文只写结论与"依已确认口径"；推理留在本台账。
5. **`--gate phase2` 的影响**：本台账里状态为 `open` 的行**不直接**阻断阶段二；阶段二闸门看的是**报告 `## 待确认项` 一节**是否还有未关闭项。报告中的待确认项与本台账必须对应（同一问题用同一 OQ-ID）。

## OQ-ID 命名

`OQ-<文献简称>-<首个出现页>-<两位序号>`，例：`OQ-BDA3-476-01`。

## 状态取值

| 状态 | 含义 | 报告里怎么表现 |
|---|---|---|
| `open` | 未解决，等待确认 | 写入 `## 待确认项`，带 OQ-ID |
| `resolved` | 已确认，答案已填 | 只采用答案，不在报告的待确认项里出现 |
| `answered` | 已有答复但可能随版本/章节变化，需留意 | 采用答案，并注明确认日期 |
| `void` | 后来发现是伪问题（如原文其实讲清楚了） | 不再使用；保留行以备追溯 |

---

## 台账

| OQ-ID | 类型 | 问题 | 出处（文献·页·图/式） | 我的处理 / 假设 | 答案（人工填） | 状态 |
|---|---|---|---|---|---|---|
| `OQ-BDA3-476-01` | 跨页依赖 | §19.1 的实体究竟是 “Figure 19.3” 还是 “Table 19.3”？（报告附录曾写作“表 19.3”） | BDA3 · 书 p.473 = PDF 488 | 第二轮回书核对图注；报告正文全篇用“图 19.3”，附录标题已统一 | 书上是 **Figure 19.3**，图注原文：“Figure 19.3 Example of measurements y from a plate as analyzed by standard software used for dilution assays.”。报告已统一为“图 19.3” | resolved |
| `OQ-BDA3-476-02` | 跨页依赖 | “高/低剂量代谢比例的相关性”与“受试者 A 与 E 之间约两倍差异”实体在哪一页？ | BDA3 · 书 p.482 = PDF 497（图形实体见 p.483） | 报告原有 3 处挂在 p.483；已回书定位并改为 p.482，图 19.8 仍标 p.483 | 在 **p.482** 正文：“The figure shows the correlation between the high-dose and the low-dose estimates of the fraction metabolized in the six people. Large variations exist between individuals; for example, a factor of two difference is seen between subjects A and E.”。图 19.8 的图形与图注实体在 p.483（PDF 498） | resolved |
| `OQ-BDA3-477-03` | 跨页依赖 | “0.001 ppm 对应环境暴露水平、50 ppm 对应职业暴露水平”在哪一页？ | BDA3 · 书 p.482 = PDF 497 | 报告 §3.4 原挂在 p.483；已回书定位并改为 p.482 | 在 **p.482**：“We selected these two levels to illustrate the inferences from the model; the high level corresponds to occupational exposures and the low level to environmental exposures of PERC.” | resolved |
| `OQ-BDA3-476-04` | 跨页依赖 | 图 19.6 曲线形状的“正式解释”与 §19.2 的“五个要素”总结，是否确在 p.483 / p.485（= 报告追回的两处）？ | BDA3 · 书 p.483 = PDF 498；书 p.485 = PDF 500 | 第二轮按用户提示回书逐句核对 | 两处追回均属实：p.483 有 “At low exposures the fraction metabolized remains constant, since metabolism is linear. Saturation starts occurring above 1 ppm and is about complete at 10 ppm.”；p.485 有 “Our analysis has five key features, all of which work in combination: …”。报告标注无误 | resolved |
| `OQ-BDA3-476-05` | 术语口径 | 图 19.3 的 “Dilution” 列取值 1、1/3、1/9、1/27 是“稀释后占原样的比例”还是“稀释倍数”？ | BDA3 · 书 p.473 = PDF 488；公式 (19.4)（p.475） | 按 (19.4) x_i = d_i · x_j^init，d_i 为相对初始稀释的比例；报告 §2.5 细节③ 已按“比例”解释 | 是**比例**（1/3 的孔要**乘以 3** 才能还原）；误读为倍数 3 会差 9 倍。此为报告中已标注的口径，登记以备后续页复用 | resolved |

<!--
新行追加在表格末尾。示例行（第一行）在台账正式使用后可以删除。
类型建议取值：术语口径 / 原文笔误 / 需要拍板的假设 / 跨页依赖 / 单位与量纲 / 导师已确认的表述
-->
