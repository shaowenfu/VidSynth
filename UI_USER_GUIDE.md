# VidSynth 系统使用与原理指南

**版本**: 1.0
**最后更新**: 2025-12-05
**适用对象**: 用户 / 开发者 / 评审老师

---

## 📖 第一部分：快速上手 (User Guide)

### 1. 系统简介
VidSynth 是一个智能视频编排系统。简单来说，你只需要给它一堆原始视频素材，告诉它你想看什么（比如“海滩度假”或“猫咪玩耍”），它就会自动从素材中把相关片段挑出来，剪辑成一个连贯的短视频。

### 2. 环境准备

#### 前置要求
确保你的电脑上安装了以下软件：
*   **Python 3.8+**: 运行程序的基础环境。
*   **FFmpeg**: 视频处理工具（用于最后的剪辑）。

#### 安装步骤
在终端（Terminal）或命令行中执行以下命令：

```bash
# 1. 创建虚拟环境（推荐，防止污染电脑环境）
python -m venv venv
source venv/bin/activate  # Windows用户请使用: venv\Scripts\activate

# 2. 安装 VidSynth 及其依赖
pip install -e .
```

### 3. 五步走操作流程

假设你有一个记录假期的长视频 `assets/raw/vacation.mp4`，你想从中剪出一个关于“海滩”的集锦。

#### Step 0: 准备数据
将你的视频文件放在项目目录下的 `assets/raw/` 文件夹中。

#### Step 1: 视频切分 (Segment)
这一步是将长视频切成一个个小的语义片段（Clip），并提取视觉特征。

```bash
# 命令格式：vidsynth segment-video <视频路径> -o <输出JSON路径>
vidsynth segment-video assets/raw/vacation.mp4 -o output/clips.json
```
*   **输出**: `output/clips.json`。这个文件里存了成百上千个小片段的信息。

#### Step 2: 主题匹配 (Match)
告诉系统你想找什么。这里我们找“beach” (海滩)。

```bash
# 命令格式：vidsynth match-theme <片段JSON路径> "<关键词>" -o <得分JSON路径>
vidsynth match-theme output/clips.json "sandy beach, ocean" -o output/scores.json
```
*   **输出**: `output/scores.json`。系统给每个片段打了个分，分越高说明越像海滩。

#### Step 3: 自动编排 (Sequence)
系统根据分数，把最好的片段挑出来，连成一个列表。

```bash
# 命令格式：vidsynth sequence-clips <片段JSON> <得分JSON> -o <剪辑表路径>
vidsynth sequence-clips output/clips.json output/scores.json -o output/edl.json
```
*   **输出**: `output/edl.json`。这是最终的“剪辑决定表”（EDL），记录了要保留哪些时间段。

#### Step 4: 导出成片 (Export)
最后，让系统根据剪辑表，生成最终的 MP4 视频。

```bash
# 命令格式：vidsynth export-edl <剪辑表路径> <原始视频路径> -o <最终视频路径>
vidsynth export-edl output/edl.json assets/raw/vacation.mp4 -o output/final_beach.mp4
```
*   **成果**: 打开 `output/final_beach.mp4`，欣赏你的作品吧！

---

## 🧠 第二部分：技术原理解析 (Deep Dive)

本部分详细阐述系统的设计思路、实现原理及代码结构，适合开发者和指导老师阅读。

### 核心设计哲学
*   **MVP (Minimum Viable Product)**: 优先保证全流程跑通，不追求单点最优。
*   **纯视觉优先**: 暂时忽略音频语义，利用 CLIP 强大的图文对齐能力解决核心问题。

### Step 1: 智能切分 (The Eyes)

#### 📍 代码位置
*   **核心模块**: `src/vidsynth/segment/`
*   **入口函数**: `src/vidsynth/segment/clipper.py` -> `segment_video`

#### 🧐 做了什么
将连续的视频流转化为离散的、具有独立语义的片段（Clip）集合。

#### 💡 怎么做的
1.  **抽帧**: 以 1fps 的频率对视频进行采样。
2.  **特征提取**: 使用 CLIP 模型（或 Mean Color）提取每一帧的视觉向量。
3.  **边界检测**: 计算相邻帧的 **Embedding 余弦距离** 和 **颜色直方图差异**。
4.  **切分**: 当差异超过设定的双阈值时，认为发生了转场（Shot Change），在此处切断。

#### 🤔 为什么这么做
*   **为什么是 1fps？**
    *   相比逐帧分析，1fps 能将计算量降低 25-60 倍，且对于“寻找素材”这一任务，秒级的颗粒度已经足够。
*   **为什么存 Embedding？**
    *   特征提取是最耗时的步骤。我们将提取好的向量（`vis_emb_avg`）存入 JSON，后续的主题匹配（Step 2）可以直接在向量空间进行，无需再次读取巨大的视频文件，实现毫秒级检索。

#### 🚀 以后会怎么做
*   引入 `PySceneDetect` 等专业库进行更精准的镜头检测（如渐变转场识别）。
*   支持动态采样率，在画面变化剧烈时自动提高采样频率。

### Step 2: 语义匹配 (The Brain)

#### 📍 代码位置
*   **核心模块**: `src/vidsynth/theme_match/`
*   **打分逻辑**: `src/vidsynth/theme_match/matcher.py` -> `ThemeMatcher.score_clips`

#### 🧐 做了什么
理解用户的文字意图，并在视频片段库中找到最匹配的画面。

#### 💡 怎么做的
1.  **Prompt 扩展**: 将用户输入的简单词（如 "beach"）扩展为一组正向描述（如 "blue sky, sand, waves"）和一组负向/对照描述（如 "forest, city, indoor"）。
2.  **零样本匹配**: 利用 CLIP 的 Text Encoder 将描述转为向量。
3.  **差值打分**: 计算片段向量与正向描述的相似度 ($S_{pos}$) 和与负向描述的相似度 ($S_{neg}$)。
    $$Score = S_{pos} - S_{neg}$$

#### 🤔 为什么这么做
*   **为什么要引入负向对照组？**
    *   CLIP 有时会关注非语义特征（如色调）。如果不加对照组，明亮的室内场景可能会被误判为“阳光沙滩”。通过减去对照组的得分，可以有效抵消这种系统性偏差，显著提高准确率。

#### 🚀 以后会怎么做
*   引入 LLM (如 GPT/Deepseek) 自动生成高质量的 Prompt 原型，减少用户输入负担。
*   引入时序模型 (Video-CLIP) 以理解“动作”（如“跑步”、“跳舞”），而不仅仅是静态场景。

### Step 3: 序列编排 (The Director)

#### 📍 代码位置
*   **核心模块**: `src/vidsynth/sequence/`
*   **编排逻辑**: `src/vidsynth/sequence/strategy.py` -> `HysteresisSequencer`

#### 🧐 做了什么
从打分结果中筛选出片段，并整合成一条连贯的时间线。

#### 💡 怎么做的
1.  **迟滞阈值 (Hysteresis Thresholding)**: 设定高阈值 ($T_{high}$) 和低阈值 ($T_{low}$)。
    *   只有得分超过 $T_{high}$ 的片段才会被选中作为“种子”。
    *   一旦选中，只要后续片段得分不低于 $T_{low}$，就继续保持选中状态。
2.  **合并**: 将时间上连续的选中片段合并为一个长片段。

#### 🤔 为什么这么做
*   **为什么用双阈值？**
    *   视频内容的语义变化通常是连续的。如果只用单一阈值，得分在阈值附近波动时，会导致视频被切得支离破碎（上一秒选中，下一秒丢弃，再下一秒又选中）。迟滞策略能有效保证片段的**时间连贯性**。

#### 🚀 以后会怎么做
*   支持多源视频混合编排（从多个视频文件中凑出一个故事）。
*   引入音乐节奏检测，让视频剪辑点卡在音乐的拍子上（On-beat cutting）。

### Step 4: 渲染导出 (The Editor)

#### 📍 代码位置
*   **核心模块**: `src/vidsynth/export/`
*   **导出逻辑**: `src/vidsynth/export/renderer.py` -> `FFmpegExporter`

#### 🧐 做了什么
执行物理层面的剪辑、拼接和编码工作。

#### 💡 怎么做的
1.  **读取 EDL**: 解析 Step 3 生成的剪辑列表。
2.  **音频处理**: 对每个片段的音频首尾添加 150ms 的淡入淡出（Fade-in/Fade-out）。
3.  **拼接**: 调用 FFmpeg 的 `concat` 滤镜将所有片段无缝拼接。

#### 🤔 为什么这么做
*   **为什么处理音频？**
    *   直接硬切（Hard Cut）会导致波形截断，产生刺耳的“爆音”。简单的淡入淡出是提升听感性价比最高的手段。

#### 🚀 以后会怎么做
*   支持视觉转场特效（如叠化 Cross-dissolve、黑场 Fade-to-black）。
*   支持自动混音（Auto-ducking），在有人声时自动降低背景音乐音量。