#  Theme-driven Multi-Source Video Trimming

##  任务背景：

主题驱动的多源视频自动编排系统
输入：一个主题关键词（如 “滑雪”、“智能手机”、“宠物陪伴”）
输出：一个主题连贯、风格一致、可观看的短视频。
系统自动从海量长短不一的原始视频中，检索、筛选、剪辑、编排并输出最终视频。

###  北极星目标

**输入**：主题关键词（例：场景1“沙滩”，场景2“智能手机”）

**输出**：与主题高度契合、连贯可看的短片（由多视频片段拼接）

##  MVP原则：

- 按“第一性原理 + 奥卡姆剃刀”来从零设计，一个**纯视觉优先**、能马上跑起来的最小系统（MVP）。思路是：只用“用户给定主题 → 视觉理解 → 片段库 → 简单编排 → 导出成片”。字幕只作可选补充，不依赖。
- 使用大模型调用来做各个硬编码效果不好部分的工作，使整个系统先平滑高效运行。

##  Step1：片段切分

- 输入：一个视频集
    - 格式：
        
        ```json
        {
          "video_id": "xxx",
          "path": "xxx"
        }
        ```
        
- 输出：一个片段集
    - 格式：(MVP阶段只实现核心字段，保留可扩展性，后续会加入更多的指标来辅助剪辑）
        
        ```json
        {
          "video_id": "xxx",
          "clip_id": 12,
          "t_start": 36.0,
          "t_end": 41.5,
          "fps_keyframe": 1,
          "vis_emb_avg": [ ... ],            // 512 or 768 dims
          "emb_model": "clip-vit-b/32@v1",
          "created_at": "...",
          "version": 1
        }
        
        ```
        
        - 其中 `vis_emb_avg` 是该片段内关键帧embedding的均值（ViT/CLIP等）。
- 切分逻辑：
    
    对每条原始视频：以 **1 fps 取关键帧**（足够快），并做**简易镜头分割**（shot/scene split）：
    
    - 方案：相邻帧的**视觉embedding余弦距离** + **直方图差异**混合阈值，距离大→切点。
    - 得到**候选片段**（clip），初始长度约 **2–6s**（按切点合并相邻高相似帧）。
- 原理：
    - 当余弦距离**很小**时，表示这两帧在**语义上是相似的**（例如，同一个人物在做同一个动作，或同一个场景的微小运动）。
    - 当余弦距离**突然增大**时，表示画面中的**核心内容或场景发生了重大变化**（例如，从“海滩”切到“餐厅”，或从“人脸特写”切到“风景广角”）。
    - 像素级或直方图差异能更灵敏地捕捉到**瞬间的、低层次的（Low-level）**视觉变化。
    - **混合策略：** 设定两个阈值，例如：
        - `IF (Cosine_Distance > $\text{Threshold}_C$) OR (Histogram_Difference > $\text{Threshold}_H$) THEN 切点`
    - 这样可以确保捕捉到语义（CLIP 擅长）和快速的视觉突变（直方图擅长）。
- 目标：片段切分足够原子化，为后续的拼接和检索提供扎实地基，每个片段的信息细粒度足够高，并且vis_emb_avg能很好反映该片段信息，避免之后重复切分和embedding操作，片段级**视觉embedding**（可永久复用）。

##  Step2：主题匹配（纯视觉）

- 输入：片段集 + 主题
- 输出：片段在主题上的得分数组
- 具体逻辑
    - 用**同一个视觉-文本对齐模型**（如 CLIP）做**零样本匹配**：
        - 把用户主题变成**一组简短文本描述**（少而精），称为**主题原型**：
            - 场景1（旅行-沙滩）：
                
                `["a sandy beach", "people playing at the beach", "ocean shoreline", "swimming in sea", "sunbathing at beach"]`
                
            - 场景2（电子测评-智能手机）：
                
                `["a smartphone close-up", "a person holding a smartphone", "smartphone on a table", "reviewing a phone"]`
                
        - 同时准备**若干对照原型**（非目标主题，避免误检）：
            - 沙滩的对照：`"mountain trail", "city street", "indoor kitchen", "snow ski slope"`
            - 手机的对照：`"laptop keyboard", "desktop monitor", "camera lens", "smartwatch"`
    - 计算每个片段 `vis_emb_avg` 与**主题原型**的相似度上界（max），记作 `S_pos`；与**对照原型**的相似度上界，记作 `S_neg`。
        
        定义**主题分数**：
        
        ```
        theme_score = S_pos - S_neg
        ```
        
- 原理
    
    > 直观：更像“沙滩/手机”，且不像“对照类”的片段得分更高。只要一个模型（CLIP）就够，简单强力。
    > 

##  Step3：片段筛选

最简单的处理：
直接把连续 `theme_score` 超阈值的候选 clip 合并，得到**更平滑的长片段**

##  Step4：片段拼接

###  镜头衔接（极简即可）

- 视觉：默认**硬切**；若相邻片段 `vis_emb` 相似度 < 阈值，则加 **150–300ms 交叉淡入淡出**
- 音频：每个片段前后 **150ms fade in/out**，避免爆音 & 硬断
- 可选：按 `vis_emb` 距离挑选“更相似的下一个”，获得**平滑过渡**（1行贪心）。

###  导出

- 导出 MP4（H.264），码率固定（如 6–8 Mbps）。
- 同时导出一个 **JSON EDL**（剪辑列表），方便复现与后续人工微调：
    
    ```json
    [
    {"video_id": "...", "t_start": 12.0, "t_end": 17.2, "reason": "beach_opening"},
    {"video_id": "...", "t_start": 83.5, "t_end": 89.0, "reason": "beach_activity"},
    ...
    ]
    ```
    

##  后续拓展：

- 兼容主题不明确或者需要系统聚类出所有可能的主题供用户选择。也就是在Step1和Step2之间加一些处理。