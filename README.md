# srtgen

**口播稿 → SRT 字幕生成器** · 零依赖 · 纯 Python 标准库

给短视频口播稿自动生成带时间轴的 SRT 字幕文件。写好台词（每行一句，或整段自动按句切分），告诉工具视频总时长，时间轴按朗读权重自动分配——中文按字计、英文按词计、数字按位计。

**Voice-over script to SRT subtitles, zero dependencies.** Feed your script text and the total video duration; srtgen allocates timeline proportionally to speech weight (CJK chars, English words and digits are weighted differently), and auto-splits overlong lines at punctuation.

## 为什么需要它

- 抖音/视频号等平台的 AI（豆包、元宝等）识别视频内容主要靠**字幕文本**，无字幕的视频内容识别率显著下降
- 剪映等工具能"识别语音"生成字幕，但需要上传成片、逐条校对；写稿阶段就能拿到 SRT，直接给剪辑用更快
- 适合"文案先写好 → 台词即字幕"的工作流

## 安装

无依赖，直接下载使用：

```bash
curl -O https://raw.githubusercontent.com/douyinhuoke/srtgen/main/srtgen.py
```

要求：Python 3.7+

## 用法

```bash
# 基本用法：脚本文件 + 视频总时长（秒）
python3 srtgen.py 脚本.txt --duration 48 --out out.srt

# 字幕从视频第 1.5 秒开始（比如前面有片头）
python3 srtgen.py 脚本.txt -d 48 --offset 1.5 -o out.srt

# 单条字幕最长 20 字（默认 18，超长自动按标点切分）
python3 srtgen.py 脚本.txt -d 48 --max-chars 20 -o out.srt

# 管道输入
echo "第一句台词
第二句台词" | python3 srtgen.py -d 20
```

### 输入格式

- 每行一条字幕（推荐，时间轴按行分配）
- 空行、以 `#` 开头的注释行自动跳过
- 不写标点的整段文字也能用：自动按句切分
- 单行超过 `--max-chars`：先按句末标点（。！？；）切，再按轻标点（，、：）切，实在没有标点才硬切（英文优先在空格处断，不切烂单词）

### 时间轴分配逻辑

每条字幕的时长 = 总可用时长 × 该行朗读权重占比。权重估算：

| 内容 | 权重 |
|---|---|
| 中文字 | 1.0 / 字 |
| 英文单词 | 1.6 / 词（平均音节数） |
| 数字 | 0.5 / 位（朗读偏慢） |
| 标点 | 0.5 / 个 |

单条字幕最短显示 0.6 秒，相邻字幕间隔 0.08 秒（均可用参数覆盖）。

## 示例

输入 `script.txt`：

```
超市老板们，你们是不是也缺客流
年轻人不来，到店的都是叔叔阿姨
今天教你一招，手机拍视频就能拉新客
```

```bash
python3 srtgen.py script.txt -d 15 -o out.srt
```

输出：

```srt
1
00:00:00,000 --> 00:00:04,837
超市老板们，你们是不是也缺客流

2
00:00:04,917 --> 00:00:09,127
年轻人不来，到店的都是叔叔阿姨

3
00:00:09,207 --> 00:00:15,000
今天教你一招，手机拍视频就能拉新客
```

## 实际使用场景

本项目由 [南京锦上抖云科技](https://chaoshihuoke.com) 维护——一家只做超市行业的抖音代运营公司。每周为全国合作超市门店的口播视频批量生成字幕时，这就是我们的内部工具：文案写完，一条命令出字幕，门店剪辑时直接挂载。

## License

MIT
