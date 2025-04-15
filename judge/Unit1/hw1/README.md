欢迎使用s7h牌评测机！

### 使用方式 

 将 `jar` 文件放在本文件夹内

打开脚本文件 `test.bat`

输入 `y` 清空 `data` 文件夹，并打开数据生成器，按照数据生成器的引导输入要测试的数据组数和递归嵌套括号的层数(一层代表允许出现单层括号)，以及是否要进一步调整更多参数

可调整的参数以及参考值会在该文件结尾给出

输入 `n`  不使用数据生成器，使用 `data` 文件夹中本身的 `.in` 文件

接下来，评测机会自动开始评测

评测所用数据和期望输出，你的输出会分别存放在data目录下的`xxx.in`，`xxx.ans`，`xxx.out` 中

### 文件树

```
project/
├── data_generator.exe
├── test.bat
├── check.py
├── target.jar       # 被测JAR文件
└── data/
    ├── 001.in		# 数据评测机自动生成或者自己预配置
    ├── 001.ans     # 自动生成
    └── 001.out     # 自动生成
```



### 可调参数&参考数值

```cpp
//not strict restrictions
int expected_expr_lenth=5;
int expected_term_lenth=3;
//the percentage of the positive sign
int positive_sign_percentage=50;
//the percentage of the three types of factors
int pow_percentage=35;
int signed_integer_percentage=35;
int expression_percentage=30;
//the three percentage should add up to 100
```





