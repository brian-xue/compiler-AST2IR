#!/usr/bin/env python3

from . import common_parser


class Parser(common_parser.Parser):
    def is_comment(self, node):
        return node.type in ["line_comment", "block_comment"]

    def is_identifier(self, node):
        return node.type == "identifier"

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
            "null": self.regular_literal,
            "true": self.regular_literal,
            "false": self.regular_literal,
            "identifier": self.regular_literal,
            "number": self.regular_number_literal,
            "string": self.string_literal,
            "template_string": self.string_literal,
            "template_substitution": self.string_substitution,
            "this": self.this_literal,
            "super": self.super_literal,
            "private_property_identifier": self.regular_literal,
            "property_identifier": self.regular_literal
        }

        return LITERAL_MAP.get(node.type, None)

    def is_literal(self, node):
        return self.obtain_literal_handler(node) is not None

    def literal(self, node, statements, replacement):
        handler = self.obtain_literal_handler(node)
        return handler(node, statements, replacement)

    def check_declaration_handler(self, node):
        DECLARATION_HANDLER_MAP = {
            "function_declaration": self.method_declaration,
            "variable_declaration": self.variable_declaration,
            "lexical_declaration": self.variable_declaration,
            "class_declaration": self.class_declaration,
            "interface_declaration": self.interface_declaration,
            "enum_declaration": self.enum_declaration,
            "type_alias_declaration": self.type_alias_declaration,
            "method_declaration": self.method_declaration,   
            "abstract_class_declaration": self.class_declaration,
            "generator_function_declaration": self.method_declaration,
            "module": self.module_declaration,
            "type_alias_declaration": self.type_alias_declaration,
            "inport_alis": self.import_declaration,
        }
        return DECLARATION_HANDLER_MAP.get(node.type, None)

    def is_declaration(self, node):
        return self.check_declaration_handler(node) is not None

    def declaration(self, node, statements):
        handler = self.check_declaration_handler(node)
        return handler(node, statements)

    def check_expression_handler(self, node):
        EXPRESSION_HANDLER_MAP = {
            "assignment_expression": self.assignment_expression,
            "assignment_pattern": self.assignment_expression,  # "assignment_pattern" is a special case of "assignment_expression
            "pattern": self.pattern,
            "rest_pattern": self.pattern,  
            "binary_expression": self.binary_expression,
            "subscript_expression": self.parse_subscript,
            "call_expression": self.call_expression,
            "unary_expression": self.unary_expression,
            "member_expression": self.member_expression,
            "ternary_expression": self.ternary_expression,
            "new_expression": self.new_expression,
            "yield_expression": self.yield_expression,
            "augmented_assignment_expression": self.augmented_assignment_expression,
            "non_null_expressopn": self.non_null_expression,
            "array": self.array,
            "parenthesized_expression": self.parenthesized_expression,
            "await_expression": self.await_expression,
            "as_expression": self.as_expression,
            "satisfies_expression": self.satisfies_expression,
            "type_assertion": self.type_assertion,
            "update_expression": self.update_expression,
            "object_assignment_pattern": self.assignment_expression,
            "pair_pattern": self.parse_pair_pattern,
            "object_pattern": self.parse_object,
            "object": self.parse_object,
            "pair": self.parse_pair_pattern,
            "spread_element": self.pattern,
            "arrow_function": self.arrow_function,
            "function_expression": self.method_declaration,
        }

        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def is_expression(self, node):
        return self.check_expression_handler(node) is not None

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
        return handler(node, statements)

    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
            "statement_block": self.statement_block,
        }
        return STATEMENT_HANDLER_MAP.get(node.type, None)

    def is_statement(self, node):
        return self.check_statement_handler(node) is not None

    def statement(self, node, statements):
        handler = self.check_statement_handler(node)
        return handler(node, statements)

    def string_literal(self, node, statements, replacement):
        replacement = []
        for child in node.named_children:
            self.parse(child,statements,replacement)

        ret = self.read_node_text(node)
        if replacement:
            for r in replacement:
                (expr, value) = r
                ret = ret.replace(self.read_node_text(expr), value)

        ret = self.handle_hex_string(ret)
        return self.handle_hex_string(ret)
        
    def string_substitution(self, node, statements, replacement):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr, statements)
        replacement.append((node, shadow_expr))
        return shadow_expr

    def this_literal(self, node, statements, replacement):
        return self.global_this()

    def super_literal(self, node, statements, replacement):
        return self.global_super()

    def parse_subscript(self,node,statements,flag = 0):
        if flag == 1: # for write
            obj = self.parse(self.find_child_by_field(node, "object"), statements)
            optional_chain = self.find_child_by_field(node, "optional_chain")
            index = self.parse(self.find_child_by_field(node, "index"), statements)
            return obj,index
        else:
            obj = self.parse(self.find_child_by_field(node, "object"), statements)
            optional_chain = self.find_child_by_field(node, "optional_chain")
            index = self.parse(self.find_child_by_field(node, "index"), statements)
            tmp_var = self.tmp_variable(statements)
            statements.append({"array_read": {"target": tmp_var, "array": obj, "index": index}})
            return tmp_var

    def non_null_expression(self, node, statements):
        self.parse(node.named_children[0], statements)

    def assignment_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        shadow_right = self.parse(right, statements)

        if left.type == "parenthesized_expression":
            shadow_left = self.parse(left, statements)
            if type(shadow_left) == list:
                child_count = len(shadow_left)
                for i in range(child_count):
                    tmp_var = self.tmp_variable(statements)
                    statements.append({"array_read": {"target": tmp_var, "array": shadow_right, "index": i}})
                    statements.append({"assign_stmt": {"target": shadow_left[i], "operand": tmp_var}})
                return shadow_left
            else:
                statements.append({"assign_stmt": {"target": shadow_left, "operand": shadow_right}})
                return shadow_left

        if left.type == "array_pattern":
            shadow_left_list = self.parse_array_pattern(left, statements)
            for i in range(len(shadow_left_list)):
                shadow_left = shadow_left_list[i]
                if right.type == "array" and i < right.named_child_count:
                    tmp_var = self.tmp_variable(statements)
                    statements.append({"array_read": {"target": tmp_var, "array": shadow_right, "index": i}})
                    statements.append({"assign_stmt": {"target": shadow_left, "operand": tmp_var}})

            return shadow_left_list


        if left.type == "subscript_expression":
            shadow_array,shadow_index = self.parse_subscript(left, statements,1)
            statements.append({"array_write": {"array": shadow_array, "index": shadow_index, "source": shadow_right}})
            return shadow_right

        if left.type == "member_expression":
            shadow_receiver_obj, shadow_field = self.member_expression(left, statements,1)
            statements.append({"field_write": {"receiver_object": shadow_receiver_obj, "field": shadow_field, "source": shadow_right}})
            return shadow_right

        shadow_left = self.read_node_text(left)
        statements.append({"assign_stmt":{"target": shadow_left, "operand": shadow_right}})
        return shadow_left


    def parse_array_pattern(self, node, statements):
        elements = node.named_children
        num_elements = len(elements)
        shadow_left_list = []
        for i in range(num_elements):
            element = elements[i]
            if self.is_comment(element):
                continue
            shadow_element = self.parse(element, statements)
            shadow_left_list.append(shadow_element)
        return shadow_left_list

    def pattern(self, node, statements):
        return self.parse(self.node.named_children[0], statements)


    def binary_expression(self, node, statements):
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator)
        right = self.find_child_by_field(node, "right")
        shadow_right = self.parse(right, statements)
        left = self.find_child_by_field(node, "left")

        if shadow_operator == "in" and left.type == "private_property_identifier":
            shadow_left = self.parse_private_property_identifier(left, statements)
        else:
            shadow_left = self.parse(left, statements)

        tmp_var = self.tmp_variable(statements)
        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_left,
                                        "operand2": shadow_right}})
        return tmp_var

    def parse_private_property_identifier(self, node, statements):
            return self.read_node_text(node)

    def call_expression(self, node, statements):
        name = self.find_child_by_field(node, "function")
        shadow_name = self.parse(name, statements)

        type_arguments = self.find_child_by_field(node, "type_arguments")
        type_text = self.read_node_text(type_arguments)[1:-1] if type_arguments else ""

        args = self.find_child_by_field(node, "arguments")
        args_list = []

        if args.named_child_count > 0:
            for child in args.named_children:
                if self.is_comment(child):
                    continue

                shadow_variable = self.parse(child, statements)
                if shadow_variable:
                    args_list.append(shadow_variable)

        tmp_return = self.tmp_variable(statements)
        statements.append({"call_stmt": {"target": tmp_return, "name": shadow_name, "args": args_list,"data_type": type_text}})

        return self.global_return()

    def unary_expression(self, node, statements):
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator)
        argument = self.find_child_by_field(node, "argument")
        shadow_argument = self.parse(argument, statements)

        tmp_var = self.tmp_variable(statements)

        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_argument}})
        return tmp_var

    def member_expression(self, node, statements,flag = 0):
        if flag == 1: # for write
            obj = self.parse(self.find_child_by_field(node, "object"), statements)
            optional_chain = self.find_child_by_field(node, "optional_chain")
            property_ = self.parse(self.find_child_by_field(node, "property"), statements)
            return obj,property_
        else:
            obj = self.parse(self.find_child_by_field(node, "object"), statements)
            optional_chain = self.find_child_by_field(node, "optional_chain")
            property_ = self.parse(self.find_child_by_field(node, "property"), statements)
            tmp_var = self.tmp_variable(statements)
            statements.append({"field_read": {"target": tmp_var, "receiver_object": obj, "field": property_}})
            return tmp_var

    def ternary_expression(self, node, statements):
        condition = self.find_child_by_field(node, "condition")
        consequence = self.find_child_by_field(node, "consequence")
        alternative = self.find_child_by_field(node, "alternative")

        condition = self.parse(condition, statements)

        body = []
        elsebody = []
        tmp_var = self.tmp_variable(statements)

        expr1 = self.parse(consequence, body)
        body.append({"assign_stmt": {"target": tmp_var, "operand": expr1}})

        expr2 = self.parse(alternative, elsebody)
        elsebody.append({"assign_stmt": {"target": tmp_var, "operand": expr2}})

        statements.append({"if": {"condition": condition, "body": body, "elsebody": elsebody}})
        return tmp_var

    def new_expression(self, node, statements):
        glang_node = {}
        constructor = self.find_child_by_field(node, "constructor")
        if constructor.type == "array":
            return self.array(constructor, statements)

        else:
            glang_node["data_type"] = self.read_node_text(constructor)

            type_parameters = self.find_child_by_field(node, "type_arguments")
            if type_parameters:
                glang_node["type_parameters"] = self.read_node_text(type_parameters)[1:-1]

            arguments = self.find_child_by_field(node, "arguments")
            argument_list = []
            if arguments.named_child_count > 0:
                for arg in arguments.named_children:
                    if self.is_comment(arg):
                        continue
                    shadow_arg = self.parse(arg, statements)
                    if shadow_arg:
                        argument_list.append(shadow_arg)

            glang_node["args"] = argument_list
            tmp_var = self.tmp_variable(statements)
            glang_node["target"] = tmp_var
            statements.append({"new_instance": glang_node})
            return tmp_var

    def yield_expression(self, node, statements):
        shadow_expr = ""
        if node.named_child_count > 0:
            expr = node.named_children[0]
            shadow_expr = self.parse(expr, statements)

        statements.append({"yield_stmt": {"target": shadow_expr}})
        return shadow_expr


    def augmented_assignment_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        shadow_right = self.parse(right, statements)
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator).replace("=", "")

        if left.type == "subscript_expression":
            shadow_array,shadow_index = self.parse_subscript(left, statements,1)
            
            tmp_var = self.tmp_variable(statements)
            statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index, }})
            tmp_var2 = self.tmp_variable(statements)
            statements.append({"assign_stmt":
                                   {"target": tmp_var2, "operator": shadow_operator,
                                    "operand": tmp_var, "operand2": shadow_right}})
            statements.append({"array_write": {"array": shadow_array, "index": shadow_index, "source": tmp_var2}})
            return tmp_var2

        if left.type == "parenthesized_expression":
            shadow_left = self.parse(left, statements)
            if type(shadow_left) == list:
                child_count = len(shadow_left)
                for i in range(child_count):
                    tmp_var = self.tmp_variable(statements)
                    statements.append({"array_read": {"target": tmp_var, "array": shadow_right,"index": str(i)}})
                    statements.append({"assign_stmt": {"target": shadow_left[i], "operator": shadow_operator,
                                                         "operand": tmp_var, "operand2": shadow_left[i]}})
                    return shadow_left
            
            else:
                statements.append({"assign_stmt": {"target": shadow_left, "operator": shadow_operator,
                                               "operand": shadow_left, "operand2": shadow_right}})
                return shadow_left

        if left.type == "member_expression":
            shadow_receiver_obj, shadow_field = self.member_expression(left, statements,1)
            tmp_var = self.tmp_variable(statements)
            statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_receiver_object, "field": shadow_field}})
            tmp_var2 = self.tmp_variable(statements)
            statements.append({"assign_stmt": {"target": tmp_var2, "operator": shadow_operator,
                                               "operand": tmp_var, "operand2": shadow_right}})
            statements.append({"field_write": {"receiver_object": shadow_receiver_object, "field": shadow_field, "source": tmp_var2}})
            return tmp_var2


        shadow_left = self.read_node_text(left)
        statements.append({"assign_stmt": {"target": shadow_left, "operator": shadow_operator,
                                               "operand": shadow_left, "operand2": shadow_right}})
        return shadow_left


    def array(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        data_type = set()
        elements = node.named_children
        for element in elements:
            data_type.add(element.type)
        data_type = list(data_type)
        statements.append({"new_array": {"target": tmp_var, "data_type": data_type}})
        num_elements = len(elements)
        for i in range(num_elements):
            element = elements[i]
            if self.is_comment(element):
                continue
            shadow_element = self.parse(element, statements)
            statements.append({"array_write": {"array": tmp_var, "index": str(i), "source": shadow_element}})
        return tmp_var

    def parenthesized_expression(self, node, statements):
        sub_expressions = node.named_children
        if sub_expressions[0].type == "sequence_expression":
            return self.parse_sequence_expression(sub_expressions[0], statements)
        else:
            return self.parse(sub_expressions[0], statements)


    def regular_literal(self, node, statements, replacement):
        return self.read_node_text(node)

    def regular_number_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        value = self.common_eval(value)
        return str(value)

    def parse_sequence_expression(self, node, statements):
        sub_expressions = node.named_children
        sequence_list = []
        for sub_expression in sub_expressions:
            if self.is_comment(sub_expression):
                continue
            sequence_list.append(self.parse(sub_expression, statements))
        return sequence_list

    def await_expression(self, node, statements):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr, statements)
        statements.append({"await_stmt": {"target": shadow_expr}})
        return shadow_expr

    def satisfies_expression(self, node, statements):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr,statements)
        typ = node.named_children[1]
        shadow_type = self.read_node_text(typ)
        statements.append({"type_assertion": {"data_type": [shadow_type], "target": shadow_expr}})
        return shadow_expr
    
    def as_expression(self, node, statements):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr,statements)
        typ = node.named_children[1]
        shadow_type = self.read_node_text(typ)
        statements.append({"type_assertion": {"data_type": [shadow_type], "target": shadow_expr}})
        return shadow_expr
    
    def parse_type_arg(self, node):
        # ???????
        ret = []
        for child in node.named_children:
            ret.append(self.read_node_text(child))
        return ret

    def type_assertion(self, node, statements):
        typ_arg = node.named_children[0]
        shadow_typ_arg = self.parse_type_arg(typ_arg)
        expr = node.named_children[1]
        shadow_expr = self.parse(expr, statements)
        statements.append({"type_assertion": {"data_type": shadow_typ_arg, "target": shadow_expr}})
        return shadow_expr

    def update_expression(self, node, statements):
        shadow_node = self.read_node_text(node)

        operator = "-"
        if "+" == shadow_node[0] or "+" == shadow_node[-1]:
            operator = "+"

        is_after = False
        if shadow_node[-1] == operator:
            is_after = True

        tmp_var = self.tmp_variable(statements)

        expression = node.named_children[0]
        if expression.type == "field_access":
            shadow_object, field = self.parse_field(expression, statements)

            statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": field}})
            tmp_var2 = self.tmp_variable(statements)
            statements.append(
                {"assign_stmt": {"target": tmp_var2, "operator": operator, "operand": tmp_var, "operand2": "1"}})
            statements.append({"field_write": {"receiver_object": shadow_object, "field": field, "source": tmp_var2}})

            if is_after:
                return tmp_var
            return tmp_var2

        if expression.type == "array_access":
            shadow_array, shadow_index = self.parse_array(expression, statements)

            statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index}})
            tmp_var2 = self.tmp_variable(statements)
            statements.append(
                {"assign_stmt": {"target": tmp_var2, "operator": operator, "operand": tmp_var, "operand2": "1"}})
            statements.append({"array_write": {"array": shadow_array, "index": shadow_index, "source": tmp_var2}})

            if is_after:
                return tmp_var
            return tmp_var2

        shadow_expression = self.parse(expression, statements)

        statements.append({"assign_stmt": {"target": tmp_var, "operand": shadow_expression}})
        statements.append({"assign_stmt": {"target": shadow_expression, "operator": operator,
                                           "operand": shadow_expression, "operand2": "1"}})

        if is_after:
            return tmp_var
        return shadow_node


    def parse_pair_pattern(self, node, statements):
        key = self.parse(node.named_children[0], statements)
        value = self.parse(node.named_children[1], statements)
        tmp_var = self.tmp_variable(statements)
        statements.append({"new_map": {"target": tmp_var,"data_type": str(type(value))}})
        statements.append({"map_write": {"map": tmp_var, "key": key, "value": value}})
        return tmp_var


    def parse_object(self, node, statements):
        obj_children = node.named_children
        tmp_var = self.tmp_variable(statements)
        statements.append({"new_array": {"target": tmp_var, "data_type": "object"}})
        for i in range(len(obj_children)):
            if self.is_comment(obj_children[i]):
                continue
            res = self.parse(obj_children[i], statements)
            statements.append({"array_write": {"array": tmp_var, "index": str(i), "source": res}})
        return tmp_var
