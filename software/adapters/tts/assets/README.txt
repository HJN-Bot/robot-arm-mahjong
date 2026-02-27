放置预录语音包的目录。

目录结构：
  polite/
    look_done.wav       -> "好，我看好了。"
    i_want_check.wav    -> "我要验牌。"
    ok_no_problem.wav   -> "牌没有问题。"
  meme/
    look_done.wav       -> "哼，给爷看完了。"
    i_want_check.wav    -> "叫验牌！"
    ok_no_problem.wav   -> "还得练啊。"

如果文件不存在，系统自动降级使用 macOS say 命令朗读。

使用 scripts/gen_tts.py 可自动生成全套语音包（需要 edge-tts）。
