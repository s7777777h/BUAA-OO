本评测机通过模拟图书馆行为进行评测。

将待测jar放在testjar文件夹下

使用`python check.py`进行评测

由于本单元进行交互式评测，`data_generator.py`负责生成静态的数据，由 `check.py` 动态生成其他数据。

静态的数据在`test_cases` 文件夹下， `results/replay_inputs` 记录了实际的输入数据，理论上只要把里面的东西直接复制到控制台里面就能复现评测情景，当然这要求你的代码不能有随机函数。

`results/logs`  里面详细记录了测试的结果。

`clean.bat` 是让评测机回到初始状态的脚本（不会删除 jar），有需要可以使用。

