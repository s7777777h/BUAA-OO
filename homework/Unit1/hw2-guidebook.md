## 面向对象设计与构造第二次作业

------

### 第一部分：训练目标

通过对数学意义上的表达式结构进行建模，完成多项式的括号展开与函数调用、化简，进一步体会层次化设计的思想的应用和工程实现。

------

### 第二部分：预备知识

- 1、1、Java 基础语法与基本容器的使用。
- 2、2、扩展 BNF 描述的形式化表述。
- 3、3、正则表达式、递归下降或其他解析方法。

------

### 第三部分：题目描述

本次作业中需要完成的任务为：读入**自定义递推函数的定义**以及一个包含幂函数、三角函数、自定义递推函数调用的**表达式**，输出**恒等变形展开所有括号后**的表达式。

在本次作业中，**展开所有括号**的定义是：对原输入表达式 �*E* 做**恒等变形**，得到新表达式 �′*E*′。其中，�′*E*′ 中不再含有自定义递推函数，且只包含**必要的括号**（必要括号的定义见**公测说明-正确性判定**）。

------

### 第四部分:迭代内容概览

在第一次作业基础上，本次迭代作业**增加**了以下几点：

- 本次作业支持嵌套多层括号。
- 本次作业新增三角函数因子，三角函数括号内部包含任意因子。
- 本次作业新增自定义递推函数因子。

------

### 第五部分：基本概念

#### 一、基本概念的声明

- **带符号整数** **支持前导 0**的**十**进制带符号整数（若为正数，则正号可以省略），无进制标识。如： `+02`、`-16`、`19260817`等。

- **因子**

  - **变量因子**

    - 幂函数
      - **一般形式** 由自变量 x，指数符号 `^` 和指数组成，指数为一个**非负**带符号整数，如：`x ^ +2`,`x ^ 02`,`x ^ 2` 。
      - **省略形式** 当指数为 1 的时候，可以省略指数符号 `^` 和指数，如：`x` 。

  - **三角函数(新增)**

    - 一般形式

       

      类似于幂函数，由

      ```
      sin(<因子>)
      ```

      或

      ```
      cos(<因子>)
      ```

       

      、指数符号

      ```
      ^
      ```

      和指数组成，其中：

      - 指数为符号不是 `-` 的整数，如：`sin(x) ^ +2`。

    - **省略形式** 当指数为 1 的时候，可以采用省略形式，省略指数符号`^`和指数部分，如：`sin(x)`。

    - 本指导书范围内的“三角函数”**仅包含`sin`和`cos`**。

  - **自定义递推函数（新增）**

    - 自定义递推函数的**定义**形如

    ```tex
    f{n}(x, y) = 递推表达式
    f{0}(x, y) = 函数表达式
    f{1}(x, y) = 函数表达式
    ```

    三者顺序任意，以换行分隔。递推表达式和函数表达式的定义见“形式化表述”部分。

    定义中默认 �>1*n*>1。

    例如

    ```tex
    f{0}(y) = y
    f{1}(y) = 1
    f{n}(y) = 1*f{n-1}(sin(y)) - 4*f{n-2}(y^2) + 1
    ```

    ```tex
    f{0}(x, y) = x - y
    f{n}(x, y) = 0*f{n-1}(x, y) + 35*f{n-2}(x, y^2)
    f{1}(x, y) = x^3 + y
    ```

    - `f` 是递推函数的**函数名**。在本次作业中，保证函数名只使用`f`，且每次只有1个自定义递推函数。 `n` 、`0` 、 `1` 是递推函数的**序号**。
    - `x`、`y` 是递推函数的形参。在本次作业中，**形参个数为 1~2 个**。形参**只使用x，y**，且同一函数定义中不会出现重复使用的形参。对一个自定义递推函数的定义来说，`f{n}`、`f{n-1}`、`f{n-2}`、…、`f{1}`、`f{0}`等一系列函数的形参统一，不会出现同一系列中函数形参不同的情况。
    - 递推表达式是一个关于形参的表达式，**保证其中 `f{n-1}`和`f{n-2}` 各被调用且只被调用 1 次**，并且调用前需要 **和一个常数因子相乘**。本次作业保证**没有其他函数调用**。函数表达式是一个关于形参的表达式。二者的一般形式见**形式化定义**。
    - 自定义递推函数的**调用**形如`f{序号}(因子, 因子)`，比如`f{3}(x^2)`，`f{5}(-1, sin(x^2)`)。
      - 大括号中为函数调用时的**序号**，你需要根据自定义递推函数的定义找到序号对应的函数，才能计算。保证0≤0≤序号≤5≤5。
      - 小括号中的`因子`为函数调用时的**实参**，包含任意一种因子。

  - **常数因子** 包含一个带符号整数，如：`233`。

  - **表达式因子** 用一对小括号包裹起来的表达式，可以带指数，且指数为一个**非负**带符号整数，例如 `(x^2 + 2*x + x)^2` 。表达式的定义将在表达式的相关设定中进行详细介绍。

- **项** 由乘法运算符连接若干因子组成，如 `x * 02`。此外，**在第一个因子之前，可以带一个正号或负号**，如 `+ x * 02`、`- +3 * x`。注意，**空串不属于合法的项**。

- **表达式** 由加法和减法运算符连接若干项组成，如： `-1 + x ^ 233 - x ^ 06 +x` 。此外，**在第一项之前，可以带一个正号或者负号，表示第一个项的正负**，如：`- -1 + x ^ 233`、`+ -2 + x ^ 19260817`。注意，**空串不属于合法的表达式**。

- **空白字符** 在本次作业中，空白字符仅包含空格 `<space>`（ascii 值 32）和水平制表符 `\t`（ascii 值 9）。其他的空白字符，均属于非法字符。

  对于空白字符，有以下几点规定：

  - 带符号整数内不允许包含空白字符，注意**符号与整数之间**也不允许包含空白字符。
  - `sin` 和 `cos` ，`f{序号}`关键字中不允许包含空白字符
  - 因子、项、表达式，在不与前两条条件矛盾的前提下，可以在任意位置包含任意数量的空白字符。

#### 二、设定的形式化表述

- 表达式 →→ 空白项 [加减 空白项] 项 空白项 | 表达式 加减 空白项 项 空白项
- 项 →→ [加减 空白项] 因子 | 项 空白项 '*' 空白项 因子
- 因子 →→ 变量因子 | 常数因子 | 表达式因子
- 变量因子 →→ 幂函数 | 三角函数 | 函数调用
- 函数调用 →→ 自定义递推函数**调用**
- 常数因子 →→ 带符号的整数
- 表达式因子 →→ '(' 表达式 ')' [空白项 指数]
- 幂函数 →→ 自变量 [空白项 指数]
- 自变量 →→ 'x'
- 三角函数 →→ 'sin' 空白项 '(' 空白项 因子 空白项 ')' [空白项 指数] | 'cos' 空白项 '(' 空白项 因子 空白项 ')' [空白项 指数]
- 指数 →→ '^' 空白项 ['+'] 允许前导零的整数 **(注：指数一定不是负数)**
- 带符号的整数 →→ [加减] 允许前导零的整数
- 允许前导零的整数 →→ ('0'|'1'|'2'|…|'9'){'0'|'1'|'2'|…|'9'}
- 空白项 →→ {空白字符}
- 空白字符 →→ （空格） | `\t`
- 加减 →→ '+' | '-'
- 换行 →→ `\n`

**自定义递推函数相关(相关限制见“公测数据限制”)**

- 自定义递推函数定义 →→ 定义列表
- 定义列表 →→ 初始定义 换行 初始定义 换行 递推定义 | 初始定义 换行 递推定义 换行 初始定义 | 递推定义 换行 初始定义 换行 初始定义
- 初始定义 →→ 'f' '{' 初始序号 '}' 空白项 '(' 空白项 形参自变量 空白项 [',' 空白项 形参自变量 空白项] ')' 空白项 '=' 空白项 函数表达式
- 初始序号 →→ '0' | '1'
- 递推定义 →→ 'f{n}' 空白项 '(' 空白项 形参自变量 空白项 [',' 空白项 形参自变量 空白项] ')' 空白项 '=' 空白项 递推表达式
- 序号 →→ '0'|'1'|'2'|'3'|'4'|'5'
- 形参自变量 →→ 'x' | 'y'
- 自定义递推函数**调用** →→ 'f{' 序号 '}' 空白项 '(' 空白项 因子 空白项 [',' 空白项 因子 空白项] ')'
- 自定义递推函数调用n-1 →→ 'f{n-1}' 空白项 '(' 空白项 因子 空白项 [',' 空白项 因子 空白项] ')'**（注：本次作业中此处的因子不允许出现任何函数调用）**
- 自定义递推函数调用n-2 →→ 'f{n-2}' 空白项 '(' 空白项 因子 空白项 [',' 空白项 因子 空白项] ')'**（注：本次作业中此处的因子不允许出现任何函数调用）**
- 递推表达式 →→ 常数因子 空白项 '*' 空白项 自定义递推函数调用n-1 空白项 加减 空白项 常数因子 空白项 '*' 空白项 自定义递推函数调用n-2 [空白项 '+' 空白项 函数表达式]
- 函数表达式 →→ 表达式（将自变量扩展为形参自变量） **(注：本次作业中函数表达式不允许出现任何函数调用)**

形式化表述中`{}[]()|`符号的含义已在第一次作业指导书中说明，不再赘述。

式子的具体含义参照其数学含义。

若输入字符串能够由“表达式”推导得出，则输入字符串合法。

除了满足上述形式化表述之外，我们本次作业的输入数据的**额外限制**请参见**第六部分：输入/输出说明 的数据限制部分**。

------

### 第六部分：输入/输出说明

#### 一、公测说明

##### 输入格式

本次作业的输入数据包含若干行：

- 第一行为一个整数 n= 0, 1，表示**自定义递推函数定义的个数**。
- 第 2 到第 3n+1 行，每行一个字符串，每三行表示一组自定义递推函数的定义。
- 第 3n+2 行，一行字符串，表示待展开表达式。

##### 输出格式

输出展开括号之后，不再含有自定义递推函数，且只包含**必要的括号**的表达式。（必要括号的定义见**公测说明-正确性判定**）。

##### 数据限制

- 输入表达式**一定满足**基本概念部分给出的**形式化描述**。

- 自定义递推函数定义

  满足以下限制：

  - 本次作业函数名一定为 `f`。
  - 函数表达式中不允许调用任何函数。**(注：但函数调用时实参可以使用自己或其他的函数，即下面的例子)**
  - 函数定义时`f{1}(x, y) = f{0}(1, 2)`,不合法。
  - 函数调用时`f{3}(f{0}((2*x),x),f{1}((x-1), 0))`,合法。
  - 函数形参不能重复出现，即无需考虑 `f{n}(x,x)=...` 这类情况
  - 函数定义式中出现的变量都必须在形参中有定义

- 对于规则 “指数 →→ ^ 空白项 ['+'] 允许前导零的整数”，我们本次要求**输入数据的指数不能超过 8**。

- 在表达式化简过程中，如果遇到了`0^0`这种情况，默认`0^0` = 1。

- 为了避免待展开表达式或函数表达式过长。最后一行输入的待展开表达式的**有效长度**至多为 200 个字符，自定义递推函数定义时，每个定义的**有效长度**至多为 75 个字符。其中**有效长度**指的是去除掉所有**空白符**后剩余的字符总数。

- 根据文法可以注意到，整数的范围并不一定在`int`或`long`范围内。

##### 判定模式

本次作业中，对于每个测试点的判定分为**正确性判定**和**性能判定**。其中，正确性判定总分为 85 分，性能判定总分为 15 分，本次作业得分为二者之和。

注意：**获得性能分的前提是，在正确性判定环节被判定为正确**。如果被判定为错误，则性能分为0分。

- 正确性判定
  - 输出的表达式须符合表达式的**形式化描述**，需要**展开所有括号**且与保持原表达式**恒等**。
  - 展开所有括号的定义：对原输入表达式做恒等变形，得到新表达式不再含有自定义递推函数，且只包含必要的括号
    - 三角函数调用时必要的一层括号：`sin()` 与 `cos()`。
    - 三角函数**对应的嵌套因子**为**不带指数的表达式因子**时，该表达式因子两侧必要的一层括号：`sin((x+x))` 与 `cos((x*x))`。（注意是“不带指数“的表达式因子，如果是`sin((x+1)^2)`,这**并不符合必要括号**的定义，你必须将其展开为`sin((x^2+2*x+1))`这种类似的形式才是合法的）
    - 同样，例如 `sin(1)` 与 `sin((1))` 均为展开形式，但 `sin(((1)))` 不是，因为后者除了函数调用和三角嵌套表达式因子的一层括号外，还包括了表达式内嵌套表达式的括号

#### 二、互测说明

互测时，你可以通过提交**输入数据**和**预期正确输出**，该组数据会被用来测试同一个互测房间中的其他同学的程序。输入数据必须符合上述的文法规则,并且满足代价函数要求。提交的预期输出只需要包含一行。

##### 数据限制

- 输入表达式**一定满足**基本概念部分给出的**形式化描述**。
- 对于规则 “指数 →→ ^ 空白项 ['+'] 允许前导零的整数”，我们本次要求**输入数据的指数不能超过 8**。
- 最终输入表达式的**有效长度**至多为 **50** 个字符。其中输入表达式的**有效长度**指的是输入表达式去除掉所有**空白符**后剩余的字符总数。（**本条与公测部分的限制不同**）
- 自定义递推函数定义时，递推定义的有效长度至多**50**个字符，初始定义的有效长度至**30**个字符。有效长度定义同上
- 除此之外，为了限制不合理的 hack，我们要求输入表达式的代价 `Cost(Expr) <= 5000`，同时要求自定义递推函数的代价`Cost(Func)<=2000`。注意，对于递推函数 `f{n}`，需要保证对于任意 0≤�≤50≤*i*≤5，`cost(f{i})<=2000`。其中表达式和自定义递推函数代价的计算方法如下（**本条与公测部分的限制不同**）：

##### 代价函数

- `Cost(常数) = max(1, len(常数))`（常数的前导零不算在其长度内）

- `Cost(x) = 1 = Cost(y)` （保证`y`仅在自定义递推函数中出现）

- `Cost(a + b) = Cost(a - b) = Cost(a) + Cost(b)`

- `Cost(a * b) = Cost(a) * Cost(b)`（多项相乘时从左到右计算）

- `Cost(sin(a)) = Cost(cos(a)) = Cost(a) + 1`

- ```
  Cost(a ^ b) =
  ```

  - 若a是单变量因子，`Cost(a ^ b) = 1`
  - 若a是表达式因子`(c)`，`Cost(a ^ b) = max(Cost(c), 2) ^ max(b,1)`
  - 若a是三角函数因子, `Cost(a ^ b) = 2 ^ b + Cost(a)`

- `Cost(+a) = Cost(-a) = Cost(a) + 1`

- `Cost(f{i}) = Cost(f{i}')*2`, `f{i}`是自定义递推函数调用，其中 `f{i}'` 是将调用 `f{i}` 的参数**作为表达式因子**代入后，所得到的表达式。同时注意`f{i}`的实参代价不能超过阈值500。

- `Cost(f{i}) = Cost(e)`,其中`f{i}`是自定义递推函数，`e`是自定义递推函数`f{i}`中`=`右部的表达式，本条规则的意思是自定义递推函数的代价等于右端表达式的代价

如果提交的数据不满足上述数据限制，则该数据将被系统拒绝，且不会用来对同屋其他被测程序进行测试。

#### 三、样例

| **#** | **输入**                                                     | **输出**                                      | **说明**                               |
| ----- | ------------------------------------------------------------ | --------------------------------------------- | -------------------------------------- |
| 1     | 0 ((x+1)*(x+2))                                              | x^2+3*x+2                                     | 二重括号，去掉后再展开                 |
| 2     | 0 (sin(x^2)+cos((x+1)))^2                                    | sin(x^2)^2+2*sin(x^2)*cos((x+1))+cos((x+1))^2 | 三角函数相加后再平方展开               |
| 3     | 1 f{0}(x)=x f{1}(x)=x^2 f{n}(x)=2*f{n-1}(x)-1*f{n-2}(x) f{2}(x)+1 | 2*x^2-x+1                                     | 自定义递推函数到 n=2 的调用            |
| 4     | 1 f{0}(x,y)=x f{1}(x,y)=y f{n}(x,y)=1*f{n-1}(x^2,y)+2*f{n-2}(x,y^2)+1 f{2}((x+1),(x-1))*x | 3*x^2+2*x                                     | 两形参递推函数调用                     |
| 5     | 1 f{0}(x)=1 f{1}(x)=x f{n}(x)=2*f{n-1}(x^2)+3*f{n-2}(x^2)+-1 f{3}(sin(x))-cos(x)^2 | 4*sin(x)^4+3*sin(x)^2+3-cos(x)^2              | 在自定义递推函数参数中使用三角函数因子 |
| 6     | 0 ((x-2*(x-1))^2+sin((x*x))^2)                               | x^2-4*x+4+sin(x^2)^2                          | 多层嵌套括号并含三角函数               |
| 7     | 1 f{0}(x,y)=x+y f{1}(x,y)=x^2-y^2 f{n}(x,y)=-3*f{n-1}((x-1),y^2)+4*f{n-2}(x^2,(y-1)) f{2}(0,3)+cos((0+3))^2 | 248+cos(3)^2                                  | 二元递推函数内含负常数因子             |

------

### 第七部分：设计建议

- 在 Java程序中，不建议使用静态数组。推荐使用 `ArrayList` 、 `HashMap` 、 `HashSet`等容器来高效率管理数据对象。

- 在处理输入解析时，可以考虑采用**递归下降解析法**或是正则表达式作为工具。递归下降方法已在先导课程的作业中得到了详尽的介绍与充分的实践，**建议同学们继续沿用**这一方法。而对正则表达式相关的 API 可以了解 `Pattern` 和 `Matcher` 类。

- 这次作业看上去似乎很难，其实找对了方法后并不难。关键思想是

  “化整为零”

  ，可以这样考虑：

  - 按照文法所定义的层次化结构来建立类（如表达式、项、因子）
  - 对于每一种运算规则（乘法、加减法），可以分别单独建立类，也可以将运算规则作为层次化结构类的功能部分。

