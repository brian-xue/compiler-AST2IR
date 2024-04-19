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
        }

        return LITERAL_MAP.get(node.type, None)

    def is_literal(self, node):
        return self.obtain_literal_handler(node) is not None

    def literal(self, node, statements, replacement):
        handler = self.obtain_literal_handler(node)
        return handler(node, statements, replacement)

    def check_declaration_handler(self, node):
        DECLARATION_HANDLER_MAP = {
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
            "new_expression": self.new_instance,
            "yield_expression": self.yield_expression,
            "augmented_assignment_expression": self.augmented_assignment_expression,
            "non_null_expressopn": self.non_null_expression,
            "array": self.array,
            "parenthesized_expression": self.parenthesized_expression,
        }

        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def is_expression(self, node):
        return self.check_expression_handler(node) is not None

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
        return handler(node, statements)

    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
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
            statements.append({"assign_stmt": {"target": shadow_left, "operand": shadow_right}})

        if left.type == "array_pattern":
            shadow_left_list = self.parse_array_pattern(left, statements)
            for i in range(len(shadow_left_list)):
                shadow_left = shadow_left_list[i]
                if right.type == "array" and i < right.named_child_count:
                    tmp_var = self.tmp_variable(statements)
                    statements.append({"array_read": {"target": tmp_var, "array": shadow_right, "index": i}})
                    statements.append({"assign_stmt": {"target": shadow_left, "operand": tmp_var}})

            return shadow_left_list


        if left.type == "object_pattern":
            pass

        if left.type == "subscript_expression":
            shadow_array,shadow_index = self.parse_subscript(left, statements,1)
            statements.append({"array_write": {"array": shadow_array, "index": shadow_index, "source": shadow_right}})
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
        pass

    def unary_expression(self, node, statements):
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator)
        argument = self.find_child_by_field(node, "argument")
        shadow_argument = self.parse(argument, statements)

        tmp_var = self.tmp_variable(statements)

        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_argument}})
        return tmp_var

    def member_expression(self, node, statements):
        pass

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
        body.append({"assign_stmt": {"target": tmp_var, "operand": expr2}})

        statements.append({"if": {"condition": condition, "body": body, "elsebody": elsebody}})
        return tmp_var

    def new_instance(self, node, statements):
        glang_node = {}
        constructor = self.find_child_by_field(node, "constructor")
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
        pass


    def augmented_assignment_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        shadow_right = self.parse(right, statements)
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator).replace("=", "")

        if left.type == "subscript_expression":
            shadow_array,shadow_index = self.parse_subscript(left, statements)
            
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
            statements.append({"assign_stmt": {"target": shadow_left, "operator": shadow_operator,
                                               "operand": shadow_left, "operand2": shadow_right}})
            return shadow_left

        shadow_left = self.read_node_text(left)
        statements.append({"assign_stmt": {"target": shadow_left, "operator": shadow_operator,
                                               "operand": shadow_left, "operand2": shadow_right}})
        return shadow_left


    def array(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        elements = node.named_children
        num_elements = len(elements)
        for i in range(num_elements):
            element = elements[i]
            if self.is_comment(element):
                continue
            shadow_element = self.parse(element, statements)
            statements.append({"array_write": {"array": tmp_var, "index": i, "source": shadow_element}})
        return tmp_var

    def parenthesized_expression(self, node, statements):
        sub_expressions = node.named_children
        if sub_expressions[0].type == "sequence_expression":
            return self.parse_sequence_expression(sub_expressions[0], statements)
        else:
            statements.append({"parenthesized_expression": self.parse(sub_expressions[0])})
            return self.parse(sub_expressions[0], statements)


    def regular_literal(self, node, statements, replacement):
        return self.read_node_text(node)

    def regular_number_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        value = self.common_eval(value)
        return str(value)

    def parse_sequence_expression(self, node, statements):
        sub_expressions = node.named_children
        for sub_expression in sub_expressions:
            if self.is_comment(sub_expression):
                continue
            self.parse(sub_expression, statements)