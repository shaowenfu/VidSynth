# 脚本目录说明

收纳批处理与调研脚本（如数据下载、阈值网格搜索），保持与核心库解耦。

## 脚本列表

- `step1_preview_with_black.py`：预览视频并添加黑色条
- `step2_grid_search.py`：网格搜索阈值参数
- `step3_generate_clips.py`：根据阈值参数生成视频片段

python scripts/step1_preview_with_black.py --video assets/raw/TheBestRunningShoes.mp4 --clips output/clips_TheBestRunningShoes.json --output-dir assets/step1_results --black-duration 0.7 