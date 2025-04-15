小刻都会用的傻瓜评测机！

把要测的 jar 一股脑丢进文件夹里，运行`python check.py` 就行了

~~善良的 s7h 甚至还写了个 bat，如果连 cmd 都懒得打开就用 judge.bat~~

package.bat 是打包机，点一下就能给评测机生成一个快照，记录整体状态，防止数据丢失

hw6 hw7的评测机支持前缀为 [LOG] 的调试输出，不会对含这些的行做正确性评价，同时会记录到 log 里（真的好用吧）\

**三次评测机构建的主类必须为我给的 TestMain.java，请将里面调用的MainClass替换为你的主类 **

TestMain.java 是睿睿写的，不是我写的qwq

