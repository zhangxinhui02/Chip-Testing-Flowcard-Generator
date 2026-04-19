你需要根据客户的订单要求，参考芯片手册以及芯片测试相关规范标准，为`{CHIP_CODE}`型号的芯片生成一份芯片测试流程卡。

要求：
1. 严格遵守输出格式。
2. 禁止虚构出不存在的订单测试要求、规范标准文件。

以下<tests>标签内是客户的订单中要求的测试：

<tests>
{TESTS}
</tests>

以下<guidance>标签内是生成芯片测试流程卡的方法：

<guidance>
{GUIDANCE}
</guidance>

以下<docs>标签内是与此订单相关的芯片手册以及芯片测试规范标准文档：

<docs>

{DOCS}

</docs>

以下<format>标签内是输出格式要求：

<format>
{FORMAT}
</format>