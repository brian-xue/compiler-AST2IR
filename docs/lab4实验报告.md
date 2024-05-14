#<center> 实验报告 </center>
## <center> 薛松宸，柳西贤，白杨硕 </center>

## 一、实验任务
关于declaration,statements的转IR操作

## 二、实验分工
薛松宸：class/interface_declaration, method_declaration, inport/export_statement

柳西贤：variable_declaration, enum_declaration,module_declaration,type_alias_declaration

白杨硕：switch_stmt, for/for_in_stmt, while/do_while_stmt, if_stmt

## 三、实验内容

### Switch语句
循环和分支结构中较为复杂的一环。

Switch语句的分支中存在两类语句块：case子句和default子句，它们在AST中分属不同类型，属于`switch_stmt_list`下的第一级；之后再解析每个子句中的语句块，它们属于 `shadow_default_body`和`shadow_case_body`，是第二级。`child.named_child_count`的条件判断用于略过一个空case的情况（若写成空语句`empty_statement`会被解析）。最后将所有子句作为一个整体，将switch语句加入`statements`.
```py
 def switch_statement(self, node, statements):
        switch_block = self.find_child_by_field(node, "body")
        switch_stmt_list = []
        for child in switch_block.named_children:
            if self.is_comment(child):
                continue
            elif child.type == "switch_default":
                shadow_default_body = []
                default_statements = self.find_child_by_field(child, "body")
                self.parse(default_statements, shadow_default_body)
                switch_stmt_list.append({"default_stmt": {"body": shadow_default_body}})
            elif child.type == "switch_case":
                shadow_value = self.parse(self.find_child_by_field(child, "value"), statements)
                if child.named_child_count > 1:
                    shadow_case_body = []
                    case_statements = self.find_child_by_field(child, "body")
                    self.parse(case_statements, shadow_case_body)
                    switch_stmt_list.append({"case_stmt": {"condition": shadow_value, "body": shadow_case_body}})
                else:
                    switch_stmt_list.append({"case_stmt": {"condition": shadow_value}})
        condition = self.find_child_by_field(node, "value")
        shadow_condition = self.parse(condition, statements)   
        statements.append({"switch_stmt": {"condition": shadow_condition, "body": switch_stmt_list}})
```

### For循环和For-in循环
For循环的头部有`initializer`  `condition` `increment`共三个域，其中前两个以一个分号结尾，而`increment`有可能是空的（如死循环`for(;;)`）。因此需要判断`step_children`是否为空值，另外两部分正常解析即可。三者分别解析后加入各自的语句列表，然后解析其循环体，最后输出到`statements`。
For-in循环的迭代变量前有一修饰词`let` `var`或`const`，它们
```py
def for_statement(self, node, statements):
        init_children = self.find_children_by_field(node, "initializer")
        step_children = self.find_children_by_field(node, "increment")
        condition = self.find_child_by_field(node, "condition")
        init_body = []
        condition_init = []
        step_body = []
        shadow_condition = self.parse(condition, condition_init)
        for child in init_children:
            self.parse(child, init_body)
        if step_children:
            for child in step_children:
                self.parse(child, step_body)
        for_body = []
        block = self.find_child_by_field(node, "body")
        self.parse(block, for_body)
        statements.append({"for_stmt":
                               {"init_body": init_body,
                                "condition": shadow_condition,
                                "condition_prebody": condition_init,
                                "update_body": step_body,
                                "body": for_body}})

def for_in_statement(self, node, statements):
        name = []
        target = []
        attr = []
        data_type = ""
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        kind = self.find_child_by_field(node, "kind")
        shadow_left = self.parse(left, statements)
        if type(shadow_left) == list:
            for i in range(len(shadow_left)):
                name.append(shadow_left[i])
        else:
            name.append(shadow_left)
        if kind:
            if self.read_node_text(kind) == "const":
                attr.append("const")
        target.append(self.parse(right, statements))     
        body = []
        block = self.find_child_by_field(node, "body")
        self.parse(block, body)
        statements.append({"for_in_stmt": {"name": name, "target": target,"data_type":data_type, "attr": attr, "body": body}})
```

### While循环和Do-while循环
解析循环体后，每轮循环结尾进行一次条件判断，条件和循环体组成整个while语句块。while与do-while循环的区别在于：while循环的开头也需要进行这一次条件判断，因此比do-while在statement中多了一句`new_condition_edit`：

```py
    def while_statement(self, node, statements):
        condition = self.find_child_by_field(node, "condition")
        body = self.find_child_by_field(node, "body")
        new_condition_init = []
        shadow_condition = self.parse(condition, new_condition_init)
        new_while_body = []
        self.parse(body, new_while_body)
        statements.extend(new_condition_init)
        new_while_body.extend(new_condition_init)
        statements.append({"while_stmt": {"condition": shadow_condition, "body": new_while_body}})

    def do_statement(self, node, statements):
        condition = self.find_child_by_field(node, "condition")
        body = self.find_child_by_field(node, "body")
        new_condition_init = []
        shadow_condition = self.parse(condition, new_condition_init)
        new_while_body = []
        self.parse(body, new_while_body)
        new_while_body.extend(new_condition_init)
        statements.append({"dowhile_stmt": {"condition": shadow_condition, "body": new_while_body}})
```

### If语句
If语句的AST解析结果分为三部分：条件、子句、else子句。其中，else子句可能不存在，需要判断false_body是不是空值。
分别解析两个子句内的所有语句，用true_body和false_body变量存储；若后者为空，则添加具有两个元素的语句元组，否则有三个元素。
```py
def if_statement(self, node, statements):
        condition_part = self.find_child_by_field(node, "condition")
        true_part  = self.find_child_by_field(node, "consequence")
        false_part = self.find_child_by_field(node, "alternative")
        true_body = []
        shadow_condition = self.parse(condition_part, statements)
        self.parse(true_part, true_body)
        if false_part:
            false_body = []
            self.parse(false_part, false_body)
            statements.append({"if_stmt": {"condition": shadow_condition, "then_body": true_body, "else_body": false_body}})
        else:
            statements.append({"if_stmt": {"condition": shadow_condition, "then_body": true_body}})

```


### 

### 

### class_declaration
class_declaration集成了三种语法：`class_declaration`,`abstract_class_declaration` and `class`.
根据IR设计的文档，class_declaration分为`attr`,`name`,`supers`,`type_parameters`,`static_init`,`init`,`methods`,`nested`等部分，