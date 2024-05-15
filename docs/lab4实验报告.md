# <center> 实验报告 </center>
## <center> 薛松宸，柳西贤，白杨硕 </center>

## 一、实验任务
关于declaration,statements的转IR操作

## 二、实验分工
薛松宸：class/interface_declaration, method_declaration/arrow_function, inport/export_statement

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


### variable_declaration
variable_declaration的解析为其他的使用提供了便捷，通过检查有无`accessibility_modifier`和`override_modifier`来为`class_declaration`提供编辑，此外，需要处理一个`var`通过逗号定义多个变量的情况，我们用for循环检测变量即可。我们还需要处理数组的初始化，特殊判断`value`是否为`subscript_expression`,对于初始化部分，用`has_init`表示是否进行初始化，进行初始化额外按照文档处理即可
```py
   def variable_declaration(self, node, statements):
        # declaration
        declarators = node.named_children

        child = self.find_child_by_type(node,"accessibility_modifier")
        attr=[]
        if child:
            attr.append(self.read_node_text(child))
        child = self.find_child_by_type(node,"override_modifier")
        if child:
            attr.append(self.read_node_text(child))

        for child in declarators:
            has_init = False

            data_type = self.find_child_by_field(child, "type")
            shadow_type=""
            if data_type:
                named_cld = data_type.named_children
                if named_cld:
                    shadow_type = self.read_node_text(named_cld[0])

            name = self.find_child_by_field(child, "name")
            name = self.read_node_text(name)
            value = self.find_child_by_field(child, "value")
            if value:
                has_init = True

            if value and value.type == "subscript_expression":
                tmp_var = self.parse_subscript(value,statements)

                shadow_value = tmp_var
            else:
                shadow_value = self.parse(value, statements)

            statements.append({"variable_decl": {"attr": attr, "data_type": shadow_type, "name": name}})
            if has_init:
                statements.append({"assign_stmt": {"target": name, "operand": shadow_value}})

```

### enum_declaration
`enum_declaration`的实现可以参考下面部分`class_declaration`部分的实现，但typescript的enum要更为简单，只需要解析`name`和`body`部分即可，不用考虑类似java的复杂情况，对于`body`部分，我们参考`variable_declaration`的实现，单独处理变量和初始化
```py
    def enum_declaration(self, node, statements):
        glang_node = {}
        glang_node["attr"] = []
        glang_node["init"] = []
        glang_node["static_init"] = []
        glang_node["fields"] = []
        glang_node["member_methods"] = []
        glang_node["enum_constants"] = []
        glang_node["nested"] = []

        child = self.find_child_by_field(node, "name")
        glang_node["name"] = self.read_node_text(child)

        glang_node["supers"] = []

        child = self.find_child_by_field(node, "body")
        self.enum_body(child, glang_node)

        statements.append({"enum_decl": glang_node})

    def enum_body(self, node, glang_node):
        children = node.named_children
        if children:
            for child in children:
                if child.type == "property_identifier":
                    name = self.read_node_text(child)
                    glang_node["fields"].append(
                        {"variable_decl": {"data_type":"", "name":name}}
                    )
                else:
                    name = self.find_child_by_field(child, "name")
                    name = self.read_node_text(name)
                    glang_node["fields"].append(
                        {"variable_decl": {"data_type":"", "name":name}}
                    )
                    value = self.find_child_by_field(child, "value")
                    if value:
                        statements = []
                        shadow_value = self.parse(value, statements)
                        glang_node["init"].append(statements)
                        glang_node["init"].append({"assign_stmt": {"target": name, "operand": shadow_value}})


```

### module_declaration
直接解析`name`部分，由于中间语言没有这个declaration，我们按照之前的格式自己写了一个，对于body部分，参考stmt部分，使用列表来储存即可
```py
    def module_declaration(self,node,statements):
        name = self.find_child_by_field(node, "name")
        name = self.read_node_text(name)

        new_body = []
        child = self.find_child_by_field(node, "body")
        if child:
            for stmt in child.named_children:
                if self.is_comment(stmt):
                    continue

                self.parse(stmt, new_body)
        
        statements.append(
            {"module_decl": {"name": name, "body": new_body}})
```

### type_alias_declaration
实现上先找到 `node` 的子节点，其字段名为 "name"，并读取该节点的文本，将其存储在 `name` 变量中。

再找到 `node` 的子节点，其字段名为 "type_parameters"。如果这个子节点存在，那么读取该节点的文本，去掉首尾的字符（通常是括号或引号），并将结果存储在 `type_parameters` 变量中。

然后找到 `node` 的子节点，其字段名为 "value"，并读取该节点的文本，将其存储在 `shadow_type` 变量中。

最后将一个字典添加到 `statements` 列表中，这个字典包含了类型别名声明的所有信息，包括目标名称（`name`）、类型参数（`type_parameters`）和源类型（`shadow_type`）,返回即可。
```py
    def type_alias_declaration(self, node, statements):
        child = self.find_child_by_field(node, "name")
        name = self.read_node_text(child)

        type_parameters = self.find_child_by_field(node, "type_parameters")
        if type_parameters:
            type_parameters = self.read_node_text(child)
            type_parameters = type_parameters[1:-1]
        
        typ = self.find_child_by_field(node, "value")
        shadow_type = self.read_node_text(typ)
        
        statements.append({"type_alias_stmt": {"target": name, "type": type_parameters, "source": [shadow_type]}})
```

### class_declaration
class_declaration集成了三种语法：`class_declaration`,`abstract_class_declaration` and `class`.
根据IR设计的文档，class_declaration分为`attr`,`name`,`supers`,`type_parameters`,`static_init`,`init`,`methods`,`nested`等部分，

首先，`attr`,比较好提取，根据参考的java程序，有class,abstract等。由于IR设计总没有decorator，所以这里我把decorator也放在attr中。

然后，`name`，`type_parameters`,`supers`这三个部分直接读取即可。

比较难的是`static_init`,`init`,`methods`,`nested`这四个部分，这四个部分都是由`class_body`这个部分组成的，所以我们需要对`class_body`进行解析。

我新创建了一个函数`class_body`，用来解析`class_body`这个部分。`class_body`这个部分包含了`method_definition`,`method_signature`,`abstract_method_definition`,`public_field_defination`,`static_block`等几个部分.
这几个部分主要分为三类，`method`相关的函数可以用`method_declaration`解析，`field`相关的函数可以用类似`variable_declaration`解析，`static_block`相当于前两个的结合体。

解析`method_declaraton`时，直接调用即可。解析`public_field_defination`时,相对麻烦一些，因为涉及到了`init`和`static_init`的情况。所以，我参考java的解析，先自己创建一个statements的空列表，进行调用解析，结果存在statements中，再根据statements中的不同类型，进行指令的写入。最后是`static_block`的解析，这个部分类似于`public_field_defination`的解析，只是没有`init`的情况，并多了可能的`method_declaration`的情况。

最后，将`attr`,`name`,`supers`,`type_parameters`,`static_init`,`init`,`methods`,`nested`这些部分整合到一起，返回即可。

```py
def class_declaration(self, node, statements):
        glang_node = {}

        glang_node["attr"] = []
        glang_node["init"] = []
        glang_node["static_init"] = []
        glang_node["fields"] = []
        glang_node["member_methods"] = []
        glang_node["nested"] = []

        if node.type in self.CLASS_TYPE_MAP:
            glang_node["attr"].append(self.CLASS_TYPE_MAP[node.type])

        child = self.find_child_by_type(node, "decorator")
        if child:
            modifiers = self.parse(child)
            glang_node["attr"].extend(modifiers)

        if "abstract" in self.read_node_text(node).split():
            glang_node["attr"].append("abstract")

        name = self.find_child_by_field(node, "name")
        if name:
            glang_node["name"] = self.read_node_text(name)

        child = self.find_child_by_field(node, "type_parameters")
        if child:
            type_parameters = self.read_node_text(child)
            glang_node["type_parameters"] = type_parameters[1:-1]

        glang_node["supers"] = []
        child = self.find_child_by_type(node,"class_heritage")
        if child:
            superclass = self.read_node_text(child)
            parent_class = superclass.replace("extends", "").replace("implements","").split()
            glang_node["supers"].append(parent_class)


        child = self.find_child_by_field(node, "body")
        self.class_body(child, glang_node)

        statements.append({f"{self.CLASS_TYPE_MAP[node.type]}_decl": glang_node})
        return glang_node["name"]


    def class_body(self, node, glang_node):
        if not node:
            return

        subtypes = ["method_signature", "method_definition","abstract_method_signature"]

        for st in subtypes:
            children = self.find_children_by_type(node, st)
            if not children:
                continue

            for child in children:
                self.parse(child, glang_node["member_methods"])

        children = self.find_children_by_type(node, "public_field_definition")
        if children:
            for child in children:
                statements = []
                extra = glang_node["init"]
                if 'static' in self.read_node_text(child).split():
                    extra = glang_node["static_init"]
                self.parse(child, statements)
                for stmt in statements:
                    if "variable_decl" in stmt:
                        glang_node["fields"].append(stmt)
                    elif "assign_stmt" in stmt:
                        field = stmt["assign_stmt"]
                        extra.append({"field_write": {"receiver_object": self.global_this(),
                                                            "field": field["target"], "source": field["operand"]}})


        children = self.find_children_by_type(node, "static_block")
        if children:
            for child in children:
                extra = glang_node["static_init"]
                statements = []
                self.statement_block(self.named_children[0], statements)
                for stmt in statements:
                    if 'variable_decl' in stmt:
                        glang_node["fields"].append(stmt)
                    elif 'assign_stmt' in stmt:
                        field = stmt["assign_stmt"]
                        extra.append({"field_write": {"receiver_object": self.global_this(),
                                                            "field": field["target"], "source": field["operand"]}})
                    elif 'method_decl' in stmt:
                        glang_node["member_methods"].append(stmt)
                    else:
                        glang_node["nested"].append(stmt)
```
另外，关于`public_field_defination`的解析，基本和`variable_declaration`的解析相同，只是排除了同时定义多个变量的情况，不在此展示。

### interface_declaration
`interface_declaration`的解析和`class_declaration`有一些相似之处，前面的`attr`,`name`,`supers`,`type_parameters`解析方法和`class_declaration`基本相同，不再赘述。后面的关于`interface_body`的解析和`class_body`差异比较大，`interface_body`有`export_statement`,`property_signature`,`call_signature`,`construct_signature`,`method_signature`.
其中，`export_statement`直接调用即可，结果放在`nested`中。由于`interface_declaration`不涉及`init`和`static_init`的情况，所以不需要进行额外处理。然后，`property_signature`,调用`public_field_defination`的解析即可，结果放在`fields`中。`call_signature`有点类似于匿名函数，所以我用`arrow_function`解析，`method_signature`和`construct_signature`直接调用`method_declaration`解析即可，这些结果放在`member_methods`中。

```py
def interface_declaration(self, node, statements):
        glang_node = {}

        glang_node["attr"] = []
        glang_node["init"] = []
        glang_node["static_init"] = []
        glang_node["fields"] = []
        glang_node["member_methods"] = []
        glang_node["nested"] = []

        if node.type in self.CLASS_TYPE_MAP:
            glang_node["attr"].append(self.CLASS_TYPE_MAP[node.type])

        name = self.find_child_by_field(node, "name")
        if name:
            glang_node["name"] = self.read_node_text(name)

        child = self.find_child_by_field(node, "type_parameters")
        if child:
            type_parameters = self.read_node_text(child)
            glang_node["type_parameters"] = type_parameters[1:-1]

        glang_node["supers"] = []
        child = self.find_child_by_type(node,"extends_type_clause")
        if child:
            superclass = self.read_node_text(child)
            parent_class = superclass.replace("extends", "").replace("implements","").split()
            glang_node["supers"].append(parent_class)

        child = self.find_child_by_field(node, "body")
        self.object_type(child, glang_node)

        statements.append({f"{self.CLASS_TYPE_MAP[node.type]}_decl": glang_node})
        return glang_node["name"]


    def object_type(self, node, glang_node):
        subtypes = ["method_signature", "construct_signature"]
        for st in subtypes:
            children = self.find_children_by_type(node, st)
            if not children:
                continue

            for child in children:
                self.method_declaration(child, glang_node["member_methods"])

        children = self.find_children_by_type(node, "call_signature")
        if children:
            for child in children:
                self.arrow_function(child, glang_node["member_methods"])

        children = self.find_children_by_type(node, "property_signature")
        if children:
            for child in children:
                self.public_field_definition(child, glang_node["fields"])

        # children = self.find_children_by_type(node, "index_signature")

        children = self.find_children_by_type(node, "export_statement")
        if children:
            for child in children:
                self.export_statement(child, glang_node["nested"])
```

### method_declaration
`method_declaration`用于解析`funtion_declaration`以及类中的函数声明。`method_declaration`包括`attr`,`data_type`,`name`,`parameters`,`init`,`body`等部分。
`attr`,`data_type`,`name`直接读取即可。`parameters`部分需要调用`formal_parameter`解析。`body`部分需要调用`statement_block`解析。

`parameter`部分的解析相对复杂一些，首先，可能有多个参数，所以需要循环解析。每一个参数的在`formal_parameter`函数中。
`formal_parameter`有`attr`,`data_type`,`name`三个部分，`name`,`attr`部分直接读取即可，`data_type`部分需要对type部分进行解析，将其加到`parameter_decl`中。如果有赋值，需要额外添加一个`assign_stmt`,并append到init中。

`body`部分的解析需要调用`statement_block`解析，将结果加到`body`中。

```py
def method_declaration(self,node,statements):
        child = self.find_child_by_field(node, "name")
        name = self.read_node_text(child)

        modifiers = []
        child = self.find_child_by_type(node, "accessibility_modifier")
        if child:
            modifiers.append(self.read_node_text(child))

        child = self.find_child_by_type(node, "override_modifier")
        if child:
            modifiers.append(self.read_node_text(child))

        child = self.find_child_by_field(node, "type_parameters")
        type_parameters = self.read_node_text(child)[1:-1]


        child = self.find_child_by_field(node, "return_type")
        return_type = ""
        if child:
            named_cld = child.named_children
            if named_cld:
                return_type = self.read_node_text(named_cld[0])


        new_parameters = []
        init = []
        child = self.find_child_by_field(node, "parameters")
        if child and child.named_child_count > 0:
            # need to deal with parameters
            for p in child.named_children:
                if self.is_comment(p):
                    continue

                self.formal_parameter(p, new_parameters,init)


        new_body = []
        child = self.find_child_by_field(node, "body")
        if child:
            for stmt in child.named_children:
                if self.is_comment(stmt):
                    continue

                self.parse(stmt, new_body)

        statements.append(
            {"method_decl": {"attr": modifiers, "data_type": return_type, "name": name, "type_parameters": type_parameters,
                             "parameters": new_parameters, "init": init, "body": new_body}})

        return name

    def formal_parameter(self, node, statements,init=[]):
        modifiers = []
        child = self.find_child_by_type(node, "accessibility_modifier")
        if child:
            modifiers.append(self.read_node_text(child))

        child = self.find_child_by_type(node, "override_modifier")
        if child:
            modifiers.append(self.read_node_text(child))

        # child = self. find readonly

        child = self.find_child_by_field(node, "pattern")
        name = self.parse(child, statements)

        child = self.find_child_by_field(node, "value")
        if child:    
            value = self.parse(child, statements)
            init.append({"assign_stmt": {"target": name, "operand": value}})

        child = self.find_child_by_field(node, "type")
        data_type = ""
        if child:
            named_cld = child.named_children
            if named_cld:
                data_type = self.read_node_text(named_cld[0])

        statements.append({"parameter_decl": {"attr": modifiers, "data_type": data_type, "name": name}})

```

### arrow_function
arrow_function是一个匿名函数，它的解析和`method_declaration`有一些相似之处，但是不同之处在于，`arrow_function`没有`name`这个域，所以不需要解析`name`这个域。另外，`arrow_function`的`body`是一个表达式，或`statement_block`所以需要考虑`expression`的情况。

```py
def arrow_function(self, node, statements):
        tmp_func = self.tmp_method()
        child = self.find_child_by_field(node, "type_parameters")
        type_parameters = self.read_node_text(child)[1:-1]


        child = self.find_child_by_field(node, "return_type")
        return_type = ""
        if child:
            named_cld = child.named_children
            if named_cld:
                return_type = self.read_node_text(named_cld[0])

        
        new_parameters = []
        init = []
        child = self.find_child_by_field(node, "parameters")
        if child and child.named_child_count > 0:
            # need to deal with parameters
            for p in child.named_children:
                if self.is_comment(p):
                    continue

                self.formal_parameter(p, new_parameters,init)


        new_body = []
        body = self.find_child_by_field(node, "body")
        if body:
            if body.type == "statement_block":
                for stmt in body.named_children:
                    if self.is_comment(stmt):
                        continue

                    shadow_expr = self.parse(body, new_body)
                    if stmt == body.named_children[-1]:
                        new_body.append({"return": {"target": shadow_expr}})
            else:
                shadow_expr = self.parse(body, new_body)
                new_body.append({"return": {"target": shadow_expr}})


        statements.append({"method_decl": {"name": tmp_func, "parameters": new_parameters, "body": new_body,"data_type": return_type}})

        return tmp_func
```

### import/export_statement
根据IR文档，`import`分为`import`和`import_as`两种情况，但是根据ts的实际情况，我在IR中加上了一个`from`的参数，用于应对`import ... from ... `的情况。

总体来说，import/export的解析不难，但是需要讨论的情况多一些。import大致可以分为三种情况，`import_clause`,`import_require_clause` and 最基本的情况(`import xxx`).再对这三种情况进行分别解析即可。
    
```py
def import_statement(self, node, statements):
        child = self.find_child_by_type(node,"import_clause")
        if child:
            source = self.read_node_text(self.find_child_by_field(node, "source"))
            self.import_clause(child, statements, source)
            return

        child = self.find_child_by_type(node,"import_require_clause")
        if child:
            require_clause = self.require_clause(child, statements)
            statements.append({"import_stmt": {"name": require_clause}})
            return require_clause


        child = self.find_child_by_field(node,"source")
        if child:
            source = self.read_node_text(child)
            statements.append({"import_stmt": {"name": source}})
            return source



    def import_clause(self, node, statements,source):
        child = self.find_child_by_type(node,"namespace_import")
        if child:
            als = self.read_node_text(self.find_child_by_type(child,"identifier"))
            statements.append({"import_as_stmt": {"name": "*", "alias": als,"source": source}})
            return als

        
        child = self.find_child_by_type(node,"named_imports")
        if child:
            import_specifiers = self.named_imports(child, statements)
            statements.append({"import_stmt": {"name": import_specifiers, "source": source}})
            return 

        child = node.named_children[0]
        name = self.read_node_text(child)
        statements.append({"import_stmt": {"name": name, "source": source}})
        return        



    
    def named_imports(self, node, statements):
        import_specifiers = []
        for child in node.named_children:
            name = self.read_node_text(self.find_child_by_field(child,"name"))
            als = self.find_child_by_field(child,"alias")
            if als:
                alias = self.read_node_text(als)
                statements.append({"type_alias_stmt":{"source": name, "target": alias}})
                import_specifiers.append(name)
            else:
                import_specifiers.append(name)

        return import_specifiers

        

    def require_clause(self, node, statements):
        child = self.find_child_by_type(node,"identifier")
        name = self.read_node_text(child)

        child = self.find_child_by_field(node,"source")
        source = self.read_node_text(child)

        statements.append({"require": {"name": name, "source": source}})

        return name
```

export的情况类似，大致可以分为`export_clause`,`declaration`,以及其他的情况。对这三种情况进行分别解析即可。

```py
def export_statement(self, node, statements):
        export_stmt = {}

        source = self.find_child_by_field(node, "source")
        if source:
            export_stmt["source"] = self.read_node_text(source)

        children = self.find_children_by_field(node, "declaration")
        if children:
            shadow_declare = self.parse(children[0], statements)
            export_stmt["name"] = shadow_declare

        child = self.find_child_by_type(node, "export_clause")
        if child:
            self.export_clause(child, statements, export_stmt)

        child = self.find_child_by_type(node,"namespace_export")
        if child:
            export_stmt["name"] = "*"
            als = self.read_node_text(child.children[2])
            export_stmt["alias"] = als

        if len(node.children) > 1:
            if self.read_node_text(node.children[1]) == "*":
                export_stmt["name"] = "*"

            elif self.read_node_text(node.children[1]) == "=":
                name = self.read_node_text(node.children[2])
                export_stmt["name"] = name

        if len(node.children) > 2:
            als = self.read_node_text(node.children[2])
            if als == "namespace":
                name = self.read_node_text(node.children[3])
                export_stmt["name"] = name
                export_stmt["alias"] = als

        

        statements.append({"export_stmt": export_stmt})


    def export_clause(self, node, statements, export_stmt):
        export_stmt["name"] = []
        export_stmt["alias"] = []


        children = self.find_children_by_type(node, "export_specifier")
        for child in children:
            name = self.read_node_text(self.find_child_by_field(child, "name"))
            export_stmt["name"].append(name)

            als = self.find_child_by_field(child, "alias")
            if als:
                alias = self.read_node_text(als)
                export_stmt["alias"].append(alias)
```


## 测试用例
本次测试用例涵盖多种decl和stmt：
```ts
import { IProps,Component,IRenderable } from './IProps';
import  * as React from 'react';
import {a as b, c as d} from './IProps';

var sum = (x: number, y: number) => x + y;

try {
    console.log(sum(3, 4));
}
const enum Enum {
	C,
    A = 1,
    B = A * 2,
}
catch (e) {
    console.log(e);
}
finally {
    console.log("Finally block");
}

throw new Error("This is an error");

var m;

m = input("Enter a number");

if (m > 5)
    {
        console.log("Number is greater than 5");
    }
else
    {
        console.log("Number is less than or equal to 5");
    }


export interface ButtonProps extends IProps {
    label: string;
    onClick: () => void;
}

class Component<T extends IProps> {
    a = 3;
    props: T;
    constructor(props: T) {
        this.props = props;
    }
}


function input(message: string): number {
    return parseInt(prompt(message));
}


class Button extends Component<ButtonProps> implements IRenderable<ButtonProps> {
    render(): void {
        console.log("Rendering button");
        this.props.onClick();
    }
}

var day;

switch (day) {
    case 0:
        console.log("It is a Sunday.");
        break;
    case 1:
        console.log("It is a Monday.");
        break;
    case 2:
        console.log("It is a Tuesday.");
        break;
    case 3:
        console.log("It is a Wednesday.");
        break;
    case 4:
        console.log("It is a Thursday.");
        break;
    case 5:
        console.log("It is a Friday.");
        break;
    case 6:
        console.log("It is a Saturday.");
        break;
    default:
        console.log("No such day exists!");
        break;
}

for (let i = 0; i < 10; i++) {
    console.log(i);
}

let i = 0;

do {
    console.log("Hello");
}while (i++ < 10);

while (i++ < 30) {
    console.log("Hello");
}

function transformArray<T, U>(
    items: T[], 
    transform: (item: T) => U, 
    separator: string = ','
  ): string {
    return items.map(item => transform(item)).join(separator);
}

type MyNumber = number

module Shapes {
    export module Polygons {
        export class Triangle { }
        export class Square { }
    }
}
```

## 实验结果
```
[{'import_stmt': {'name': ['IProps', 'Component', 'IRenderable'],
                  'source': "'./IProps'"}},
 {'import_as_stmt': {'name': '*', 'alias': 'React', 'source': "'react'"}},
 {'type_alias_stmt': {'source': 'a', 'target': 'b'}},
 {'type_alias_stmt': {'source': 'c', 'target': 'd'}},
 {'import_stmt': {'name': ['a', 'c'], 'source': "'./IProps'"}},
 {'method_decl': {'name': '%m0',
                  'parameters': [{'parameter_decl': {'attr': [],
                                                     'data_type': 'number',
                                                     'name': 'x'}},
                                 {'parameter_decl': {'attr': [],
                                                     'data_type': 'number',
                                                     'name': 'y'}}],
                  'body': [{'assign_stmt': {'target': '%v0',
                                            'operator': '+',
                                            'operand': 'x',
                                            'operand2': 'y'}},
                           {'return': {'target': '%v0'}}],
                  'data_type': ''}},
 {'variable_decl': {'attr': [], 'data_type': '', 'name': 'sum'}},
 {'assign_stmt': {'target': 'sum', 'operand': '%m0'}},
 {'try_stmt': {'try_body': [{'field_read': {'target': '%v0',
                                            'receiver_object': 'console',
                                            'field': 'log'}},
                            {'call_stmt': {'target': '%v1',
                                           'name': 'sum',
                                           'args': ['3', '4'],
                                           'data_type': ''}},
                            {'call_stmt': {'target': '%v2',
                                           'name': '%v0',
                                           'args': ['@return'],
                                           'data_type': ''}}],
               'else_body': [],
               'catch_body': [{'catch_clause': {'param': 'e',
                                                'type': [],
                                                'body': [{'field_read': {'target': '%v0',
                                                                         'receiver_object': 'console',
                                                                         'field': 'log'}},
                                                         {'call_stmt': {'target': '%v1',
                                                                        'name': '%v0',
                                                                        'args': ['e'],
                                                                        'data_type': ''}}]}}],
               'finally_body': [{'finally_stmt': {'body': [{'field_read': {'target': '%v0',
                                                                           'receiver_object': 'console',
                                                                           'field': 'log'}},
                                                           {'call_stmt': {'target': '%v1',
                                                                          'name': '%v0',
                                                                          'args': ['"Finally '
                                                                                   'block"'],
                                                                          'data_type': ''}}]}}]}},
{'enum_decl': {'attr': [],
                'init': [[], {'assign_stmt': {'target': 'A', 'operand': '1'}},
                         [{'assign_stmt': {'target': '%v0',
                                           'operator': '*',
                                           'operand': 'A',
                                           'operand2': '2'}}],
                         {'assign_stmt': {'target': 'B', 'operand': '%v0'}}],
                'static_init': [],
                'fields': [{'variable_decl': {'data_type': '', 'name': 'C'}},
                           {'variable_decl': {'data_type': '', 'name': 'A'}},
                           {'variable_decl': {'data_type': '', 'name': 'B'}}],
                'member_methods': [],
                'enum_constants': [],
                'nested': [],
                'name': 'Enum',
                'supers': []}},
 {'new_instance': {'data_type': 'Error',
                   'args': ['"This is an error"'],
                   'target': '%v0'}},
 {'throw_stmt': {'target': '%v0'}},
 {'variable_decl': {'attr': [], 'data_type': '', 'name': 'm'}},
 {'call_stmt': {'target': '%v1',
                'name': 'input',
                'args': ['"Enter a number"'],
                'data_type': ''}},
 {'assign_stmt': {'target': 'm', 'operand': '@return'}},
 {'assign_stmt': {'target': '%v2',
                  'operator': '>',
                  'operand': 'm',
                  'operand2': '5'}},
 {'if_stmt': {'condition': '%v2',
              'then_body': [{'field_read': {'target': '%v0',
                                            'receiver_object': 'console',
                                            'field': 'log'}},
                            {'call_stmt': {'target': '%v1',
                                           'name': '%v0',
                                           'args': ['"Number is greater than '
                                                    '5"'],
                                           'data_type': ''}}],
              'else_body': [{'field_read': {'target': '%v0',
                                            'receiver_object': 'console',
                                            'field': 'log'}},
                            {'call_stmt': {'target': '%v1',
                                           'name': '%v0',
                                           'args': ['"Number is less than or '
                                                    'equal to 5"'],
                                           'data_type': ''}}]}},
 {'interface_decl': {'attr': ['interface'],
                     'init': [],
                     'static_init': [],
                     'fields': [{'variable_decl': {'attr': [],
                                                   'data_type': 'string',
                                                   'name': 'label'}},
                                {'variable_decl': {'attr': [],
                                                   'data_type': '() => void',
                                                   'name': 'onClick'}}],
                     'member_methods': [],
                     'nested': [],
                     'name': 'ButtonProps',
                     'supers': [['IProps']]}},
 {'export_stmt': {'name': 'ButtonProps'}},
 {'class_decl': {'attr': ['class'],
                 'init': [{'field_write': {'receiver_object': '@this',
                                           'field': 'a',
                                           'source': '3'}}],
                 'static_init': [],
                 'fields': [{'variable_decl': {'attr': [],
                                               'data_type': '',
                                               'name': 'a'}},
                            {'variable_decl': {'attr': [],
                                               'data_type': 'T',
                                               'name': 'props'}}],
                 'member_methods': [{'method_decl': {'attr': [],
                                                     'data_type': '',
                                                     'name': 'constructor',
                                                     'type_parameters': '',
                                                     'parameters': [{'parameter_decl': {'attr': [],
                                                                                        'data_type': 'T',
                                                                                        'name': 'props'}}],
                                                     'init': [],
                                                     'body': [{'assign': 'this.props '
                                                                         '= '
                                                                         'props'},
                                                              {'field_write': {'receiver_object': '@this',
                                                                               'field': 'props',
                                                                               'source': 'props'}}]}}],
                 'nested': [],
                 'name': 'Component',
                 'type_parameters': 'T extends IProps',
                 'supers': []}},
 {'method_decl': {'attr': [],
                  'data_type': 'number',
                  'name': 'input',
                  'type_parameters': '',
                  'parameters': [{'parameter_decl': {'attr': [],
                                                     'data_type': 'string',
                                                     'name': 'message'}}],
                  'init': [],
                  'body': [{'call_stmt': {'target': '%v0',
                                          'name': 'prompt',
                                          'args': ['message'],
                                          'data_type': ''}},
                           {'call_stmt': {'target': '%v1',
                                          'name': 'parseInt',
                                          'args': ['@return'],
                                          'data_type': ''}},
                           {'return_stmt': {'target': '@return'}}]}},
 {'class_decl': {'attr': ['class'],
                 'init': [],
                 'static_init': [],
                 'fields': [],
                 'member_methods': [{'method_decl': {'attr': [],
                                                     'data_type': 'void',
                                                     'name': 'render',
                                                     'type_parameters': '',
                                                     'parameters': [],
                                                     'init': [],
                                                     'body': [{'field_read': {'target': '%v0',
                                                                              'receiver_object': 'console',
                                                                              'field': 'log'}},
                                                              {'call_stmt': {'target': '%v1',
                                                                             'name': '%v0',
                                                                             'args': ['"Rendering '
                                                                                      'button"'],
                                                                             'data_type': ''}},
                                                              {'field_read': {'target': '%v2',
                                                                              'receiver_object': '@this',
                                                                              'field': 'props'}},
                                                              {'field_read': {'target': '%v3',
                                                                              'receiver_object': '%v2',
                                                                              'field': 'onClick'}},
                                                              {'call_stmt': {'target': '%v4',
                                                                             'name': '%v3',
                                                                             'args': [],
                                                                             'data_type': ''}}]}}],
                 'nested': [],
                 'name': 'Button',
                 'supers': [['Component<ButtonProps>',
                             'IRenderable<ButtonProps>']]}},
 {'variable_decl': {'attr': [], 'data_type': '', 'name': 'day'}},
 {'switch_stmt': {'condition': 'day',
                  'body': [{'case_stmt': {'condition': '0',
                                          'body': [{'field_read': {'target': '%v0',
                                                                   'receiver_object': 'console',
                                                                   'field': 'log'}},
                                                   {'call_stmt': {'target': '%v1',
                                                                  'name': '%v0',
                                                                  'args': ['"It '
                                                                           'is '
                                                                           'a '
                                                                           'Sunday."'],
                                                                  'data_type': ''}}]}},
                           {'case_stmt': {'condition': '1',
                                          'body': [{'field_read': {'target': '%v0',
                                                                   'receiver_object': 'console',
                                                                   'field': 'log'}},
                                                   {'call_stmt': {'target': '%v1',
                                                                  'name': '%v0',
                                                                  'args': ['"It '
                                                                           'is '
                                                                           'a '
                                                                           'Monday."'],
                                                                  'data_type': ''}}]}},
                           {'case_stmt': {'condition': '2',
                                          'body': [{'field_read': {'target': '%v0',
                                                                   'receiver_object': 'console',
                                                                   'field': 'log'}},
                                                   {'call_stmt': {'target': '%v1',
                                                                  'name': '%v0',
                                                                  'args': ['"It '
                                                                           'is '
                                                                           'a '
                                                                           'Tuesday."'],
                                                                  'data_type': ''}}]}},
                           {'case_stmt': {'condition': '3',
                                          'body': [{'field_read': {'target': '%v0',
                                                                   'receiver_object': 'console',
                                                                   'field': 'log'}},
                                                   {'call_stmt': {'target': '%v1',
                                                                  'name': '%v0',
                                                                  'args': ['"It '
                                                                           'is '
                                                                           'a '
                                                                           'Wednesday."'],
                                                                  'data_type': ''}}]}},
                           {'case_stmt': {'condition': '4',
                                          'body': [{'field_read': {'target': '%v0',
                                                                   'receiver_object': 'console',
                                                                   'field': 'log'}},
                                                   {'call_stmt': {'target': '%v1',
                                                                  'name': '%v0',
                                                                  'args': ['"It '
                                                                           'is '
                                                                           'a '
                                                                           'Thursday."'],
                                                                  'data_type': ''}}]}},
                           {'case_stmt': {'condition': '5',
                                          'body': [{'field_read': {'target': '%v0',
                                                                   'receiver_object': 'console',
                                                                   'field': 'log'}},
                                                   {'call_stmt': {'target': '%v1',
                                                                  'name': '%v0',
                                                                  'args': ['"It '
                                                                           'is '
                                                                           'a '
                                                                           'Friday."'],
                                                                  'data_type': ''}}]}},
                           {'case_stmt': {'condition': '6',
                                          'body': [{'field_read': {'target': '%v0',
                                                                   'receiver_object': 'console',
                                                                   'field': 'log'}},
                                                   {'call_stmt': {'target': '%v1',
                                                                  'name': '%v0',
                                                                  'args': ['"It '
                                                                           'is '
                                                                           'a '
                                                                           'Saturday."'],
                                                                  'data_type': ''}}]}},
                           {'default_stmt': {'body': [{'field_read': {'target': '%v0',
                                                                      'receiver_object': 'console',
                                                                      'field': 'log'}},
                                                      {'call_stmt': {'target': '%v1',
                                                                     'name': '%v0',
                                                                     'args': ['"No '
                                                                              'such '
                                                                              'day '
                                                                              'exists!"'],
                                                                     'data_type': ''}}]}}]}},
 {'for_stmt': {'init_body': [{'variable_decl': {'attr': [],
                                                'data_type': '',
                                                'name': 'i'}},
                             {'assign_stmt': {'target': 'i', 'operand': '0'}}],
               'condition': '%v0',
               'condition_prebody': [{'assign_stmt': {'target': '%v0',
                                                      'operator': '<',
                                                      'operand': 'i',
                                                      'operand2': '10'}}],
               'update_body': [{'assign_stmt': {'target': '%v0',
                                                'operand': 'i'}},
                               {'assign_stmt': {'target': 'i',
                                                'operator': '+',
                                                'operand': 'i',
                                                'operand2': '1'}}],
               'body': [{'field_read': {'target': '%v0',
                                        'receiver_object': 'console',
                                        'field': 'log'}},
                        {'call_stmt': {'target': '%v1',
                                       'name': '%v0',
                                       'args': ['i'],
                                       'data_type': ''}}]}},
 {'variable_decl': {'attr': [], 'data_type': '', 'name': 'i'}},
 {'assign_stmt': {'target': 'i', 'operand': '0'}},
 {'dowhile_stmt': {'condition': '%v1',
                   'body': [{'field_read': {'target': '%v0',
                                            'receiver_object': 'console',
                                            'field': 'log'}},
                            {'call_stmt': {'target': '%v1',
                                           'name': '%v0',
                                           'args': ['"Hello"'],
                                           'data_type': ''}},
                            {'assign_stmt': {'target': '%v0', 'operand': 'i'}},
                            {'assign_stmt': {'target': 'i',
                                             'operator': '+',
                                             'operand': 'i',
                                             'operand2': '1'}},
                            {'assign_stmt': {'target': '%v1',
                                             'operator': '<',
                                             'operand': '%v0',
                                             'operand2': '10'}}]}},
 {'assign_stmt': {'target': '%v2', 'operand': 'i'}},
 {'assign_stmt': {'target': 'i',
                  'operator': '+',
                  'operand': 'i',
                  'operand2': '1'}},
 {'assign_stmt': {'target': '%v3',
                  'operator': '<',
                  'operand': '%v2',
                  'operand2': '30'}},
 {'while_stmt': {'condition': '%v3',
                 'body': [{'field_read': {'target': '%v0',
                                          'receiver_object': 'console',
                                          'field': 'log'}},
                          {'call_stmt': {'target': '%v1',
                                         'name': '%v0',
                                         'args': ['"Hello"'],
                                         'data_type': ''}},
                          {'assign_stmt': {'target': '%v2', 'operand': 'i'}},
                          {'assign_stmt': {'target': 'i',
                                           'operator': '+',
                                           'operand': 'i',
                                           'operand2': '1'}},
                          {'assign_stmt': {'target': '%v3',
                                           'operator': '<',
                                           'operand': '%v2',
                                           'operand2': '30'}}]}},
 {'method_decl': {'attr': [],
                  'data_type': 'string',
                  'name': 'transformArray',
                  'type_parameters': 'T, U',
                  'parameters': [{'parameter_decl': {'attr': [],
                                                     'data_type': 'T[]',
                                                     'name': 'items'}},
                                 {'parameter_decl': {'attr': [],
                                                     'data_type': '(item: T) '
                                                                  '=> U',
                                                     'name': 'transform'}},
                                 {'parameter_decl': {'attr': [],
                                                     'data_type': 'string',
                                                     'name': 'separator'}}],
                  'init': [{'assign_stmt': {'target': 'separator',
                                            'operand': "','"}}],
                  'body': [{'field_read': {'target': '%v0',
                                           'receiver_object': 'items',
                                           'field': 'map'}},
                           {'method_decl': {'name': '%m1',
                                            'parameters': [],
                                            'body': [{'call_stmt': {'target': '%v0',
                                                                    'name': 'transform',
                                                                    'args': ['item'],
                                                                    'data_type': ''}},
                                                     {'return': {'target': '@return'}}],
                                            'data_type': ''}},
                           {'call_stmt': {'target': '%v1',
                                          'name': '%v0',
                                          'args': ['%m1'],
                                          'data_type': ''}},
                           {'field_read': {'target': '%v2',
                                           'receiver_object': '@return',
                                           'field': 'join'}},
                           {'call_stmt': {'target': '%v3',
                                          'name': '%v2',
                                          'args': ['separator'],
                                          'data_type': ''}},
                           {'return_stmt': {'target': '@return'}}]}},
    {'type_alias_stmt': {'target': 'MyNumber',
                      'type': None,
                      'source': ['number']}},
    {'module_decl': {'name': 'Shapes',
                  'body': [{'module_decl': {'name': 'Polygons',
                                            'body': [{'class_decl': {'attr': ['class'],
                                                                     'init': [],
                                                                     'static_init': [],
                                                                     'fields': [],
                                                                     'member_methods': [],
                                                                     'nested': [],
                                                                     'name': 'Triangle',
                                                                     'supers': []}},
                                                     {'export_stmt': {'name': 'Triangle'}},
                                                     {'class_decl': {'attr': ['class'],
                                                                     'init': [],
                                                                     'static_init': [],
                                                                     'fields': [],
                                                                     'member_methods': [],
                                                                     'nested': [],
                                                                     'name': 'Square',
                                                                     'supers': []}},
                                                     {'export_stmt': {'name': 'Square'}}]}},
                           {'export_stmt': {'name': None}}]}}]
```