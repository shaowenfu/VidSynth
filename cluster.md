# VidSynth 潜在主题发现模块 (Clustering Module) 系统设计

## 1. 模块目标 (Objective)

本模块旨在通过无监督学习的方式，挖掘长视频（或视频集）中的潜在视觉结构。

核心价值：

1. **数据集理解**：在不观看完整视频的情况下，回答“这个视频集包含哪些主要内容（标签）？”
2. **特征验证**：通过聚类效果（是否将相似场景聚在一起），验证 Step 1 提取的视觉 Embedding 是否有效。
3. **冷启动支持**：为用户提供可选的检索关键词建议。

## 2. 核心逻辑：过聚类与代表性采样 (Over-Clustering & Representation)

为了解决“单一片段可能包含多重语义”以及“聚类边界模糊”的问题，本系统采用以下策略：

1. **特征空间**：直接使用 Step 1 产出的 `vis_emb_avg`
2. **过聚类 (Over-Clustering)**：设定较大的 $K$ 值（例如 20-30），将特征空间切分得更细碎，以保证每个簇（Cluster）内部的**纯度（Purity）**极高。
3. **圆心提取 (Centroid Extraction)**：只关注每个簇几何中心最近的 1-3 个片段，将其作为该簇的“课代表”。
4. **视频合成**：根据聚类结果，将每个簇内的中心五个以内片段拼接起来，生成一个代表该簇的视频片段。输出到 `output/clusters/` 目录。
4. **打标签 (Labeling)**：人工打标签生成标签。（不需要编写代码）

## 3. 系统架构 (Architecture)

### 3.1 数据流图

```
graph LR
    A[Input: clips.json] --> B(特征加载与预处理)
    B --> C{聚类引擎 K-Means}
    C -->|K=20| D[簇划分 Cluster Assignment]
    D --> E[圆心计算与采样]
    E --> F[视频合成]
    F --> G[Output: clusters/]

```

### 3.2 模块组成

### A. 数据加载器 (DataLoader)

- **输入**: Step 1 生成的 `output/clips_TheBestRunningShoes.json`。
- **功能**: 提取 `vis_emb_avg` 字段，转换为 `numpy.ndarray` (Shape: `[N, D]`)。
- **预处理**: 执行 **L2 Normalization**。
    - *原因*: CLIP 向量是基于余弦相似度的，而 K-Means 基于欧氏距离。经过 L2 归一化后的欧氏距离与余弦距离单调相关，确保聚类逻辑与检索逻辑一致。

### B. 聚类引擎 (ClusterEngine)

- **算法**: `sklearn.cluster.KMeans`
- **参数策略**:
    - `n_clusters`: 动态设定。建议 $K = \min(N/5, 20)$，即每 5 个片段分一类，上限 20 类。
    - `random_state`: 固定种子 (如 42)，保证结果可复现。

### C. 视频合成器 (VideoComposer)

- **功能**:
    1. 获取聚类中心 `kmeans.cluster_centers_`。
    2. 计算每个簇内所有点到中心的距离。
    3. **Top-K 采样**: 对每个簇，选出距离中心最近的 5 个片段拼接起来作为 `Representative video`。

## 4. 数据结构设计 (Data Structures)

### 4.1 输入结构 (来自 Step 1)

```
// output/clips_TheBestRunningShoes.json
[
  {
    "clip_id": "video_01_001",
    "vis_emb_avg": [0.12, -0.05, ...], // 核心数据
    "path": "/data/video_01.mp4",
    "t_start": 0.0,
    "t_end": 5.0
  },
  ...
]

```

### 4.2 输出结构 (聚类结果)

```
// output/clusters/
{
    "clusters": [
  {
    "cluster_id": 0,
    "representative_video": "video_01_045.mp4",
    "size": 12, // 该类包含多少片段
    "potential_labels": ["会议室", "PPT演示"] // VLM生成或人工预填
  },
  "topics": [
    {
      "cluster_id": 0,
      "representative_clip": {
        "clip_id": "video_01_045",
        "timestamp": [120.5, 125.0],
        "image_path": "frames/video_01_045_mid.jpg"
      },
      "size": 12, // 该类包含多少片段
      "potential_labels": ["会议室", "PPT演示"] // VLM生成或人工预填
    },
    ...
  ]
}

```

## 5. 开发步骤与验证 (Implementation Roadmap)

### Phase 1: 核心跑通 (Priority 0)

1. **脚本编写**: 编写 `scripts/cluster_analysis.py`。
2. **功能实现**:
    - 加载 `clips.json`。
    - 执行 L2 归一化。
    - 运行 K-Means。
    - 找出每个簇中心最近的片段 ID。
3. **可视化验证**:

## 6. 关键注意事项 (Notes)

1. **K值的选择**: 宁大勿小。
    - $K$ 太小 -> 簇内混杂（Under-fitting），导致“团战”和“走路”分不开。
    - $K$ 太大 -> 簇过于细碎（Over-fitting），同一个“团战”被拆成 3 个簇。
    - *策略*: 我们宁愿要“细碎”，因为我们的目的是**发现**。细碎的簇可以通过人工归并，但混杂的簇无法拆分。
2. **降维陷阱**: 聚类时**直接在高维空间（512/768维）进行**，不要在 t-SNE 降维后的 2维空间聚类。t-SNE 仅用于可视化展示，它会丢失全局距离信息。