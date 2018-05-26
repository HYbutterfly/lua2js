# -*- coding: UTF-8 -*-

import os
import sys
import traceback
import argparse
import string
import re

global src_path
global dst_path
src_path = "E:/client/SXGames_test/games/xian/"
dst_path = "E:/client/SXGame_html5/src/games/xian/"

def Iterative(path):
	for fpath,dirs,fs in os.walk(path):
		for dir in dirs:
			#屏蔽指定文件夹
			if dir == 'images':
				continue
			mkdir = os.path.join(dst_path, dir)
			if not os.path.exists(mkdir):
				os.mkdir(mkdir)
		dpath = fpath.replace(src_path, dst_path)
		for f in fs:
			file_src = os.path.join(fpath,f)
			file_dst = os.path.join(dpath, os.path.splitext(f)[0]+'.js')
			#只转换lua文件，并且目标文件不存在
			if os.path.splitext(f)[1] == '.lua' and not os.path.exists(file_dst):
				convert_lua_2_js(file_src, file_dst)

# 插入描述
insert_descs = {
	'for' : '// @lua2js@ warning for循环 注意可能有数组下标的问题',
	'local2' : '// @lua2js@ error js不能有多个返回值',
}

# MODE = {
#     'find': 1,      # 字符串查找替换
#     'search': 2,    # 正则表达式匹配替换
# }
mode_s = 1      # 字符串查找替换
mode_re = 2     # 正则表达式匹配替换
config_replace = [
	# tab改空格
	[mode_s, '\t', '    '],
	# 统一换行
	[mode_s, '\r\n', '\n'],


	########## 注释掉不需要的 ##########

	# require和import eg:local Enum = require("games.mj_common.common.Enum")
	[mode_re, 'local *(\w+) *= *(require|import).*?\n', ''],
	# return 语句
	[mode_re, '\nreturn *(\w+)', '\n// return \g<1>'],
	# 原来的对象 local GYPlayJI = { };
	[mode_re, '\nlocal *(\w+) *= *\{', '\n// var \g<1> = {'],


	# 构造函数继承 local M = class("Shake",function ( ) return cc.ActionInterval end)
	[mode_re, '\nlocal\s+(\w+)\s*=\s*class\s*\(\s*\"(\S+?)\"\s*,\s*function\s*\(([\s\S]*?)end\)',
		'\n/*\n\g<1> = class("\g<2>"), function(\g<3>end)\n*/'],
	# 内部变量 这个应该变成对象属性,用this.访问,需要手动加上逗号
	[mode_re, '\nlocal *(\w+) *= *', '\n// \g<1> : '],


	########## 数组 ##########

	# # 数组部分还需改进,因涉及{}放在前面处理
	# # 字典数组 = -> : 加[]的索引是变量,保持= 以字符串为索引需=改为:
	# # local dataDic = { “a”=1, “b”=2, “c”=3 } // Lua
	# # var dataDic = { a:1, b:2, c:3 }         // JS
	# [mode_re, '\{([\s]*?)([\w]+?)([\s]*?)=([\s\S]*?)\}', '{\g<1>\g<2>\g<3>:\g<4>}'],
	# [mode_re, '\{([\s\S]*?),([\s]*?)([\w]+?)([\s]*?)=([\s\S]*?)\}', '{\g<1>,\g<2>\g<3>\g<4>:\g<5>}'],
	# # 标准数组要用中括号
	# # ['{', '['],
	# # ['}', ']'],


	########## ########## 语法 关键词 ########## ##########

	# end -> }
	# 这个一般是类成员函数,加个逗号
	[mode_re, '(?<=\n)end *(?=\n)', '},'],
	# 普通的end,可能是函数的,也可能是if,for,while的
	[mode_re, '(?<=\W)end(?=\W)', '}'],
	# [mode_re, '(?<=\n)( *)end(?=\W)', '\g<1>}'],
	# [mode_re, '(?<=\n)( *)(\w.*?) *end(?=\W)', '\g<1>\g<2>\n\g<1>}'],
	# [mode_re, '(?<=\W)end(?=\W)', '}'],

	########## 函数格式 ##########

	# 因为添加了\n{ 注释中的funtion()未处理正确

	# 匿名函数 function() ... end -> function() { ... }
	# 用([\w\{\(\:\.])做了限定,避免注释中的funtion()
	[mode_re, '(?<=\n)( *)([\w\{\(\:\.])(.*?)function\s*\((.*?)\)', '\g<1>\g<2>\g<3>function(\g<4>)\n\g<1>{'],

	# 局部函数 lua : local function callFunc() ... end -> js : var clickOkCallback = function() { ... }
	[mode_re, '(?<=\n)( *)local\s*function\s*(\w+?)\(([\s\S]*?)\)', '\g<1>var \g<2> = function(\g<3>)\n\g<1>{'],

	# 构造函数function M:ctor(...) 加上 this._super(...)
	[mode_re, '(?<=\n)( *)function\s+([\w]+?):(ctor) *\(([\s\S]*?)\)',
		'\g<1>\g<3> : function(\g<4>)\n\g<1>{\n    \g<1>var self = this\n    \g<1>this._super(\g<4>)'],
	# 类函数 function GYPlayJI.PlayChong(pChair) ... end -> PlayChong : function(pChair) { ... }
	[mode_re, '(?<=\n)( *)function\s+([\w]+?)[.:]([\w]+?) *\(([\s\S]*?)\)',
		'\g<1>\g<3> : function(\g<4>)\n\g<1>{\n    \g<1>var self = this'],


	########## 逻辑 ##########

	# 统一先处理下空格更好匹配
	[mode_re, '(\]\(\)\'\"])(==|~=|and|or|not)(\s*)(\(\[\'\"])', '\g<1> \g<2>\g<3>\g<4>'],
	[mode_re, '(\]\)\'\"])(\s*)(==|~=|and|or|not)(\(\[\'\"])', '\g<1>\g<2>\g<3> \g<4>'],
	# 逻辑 == -> === ; ~= -> != ; and -> && ; or -> || ; not -> ! ;
	[mode_re, '(\s+)==(\s+)', '\g<1>===\g<2>'],
	[mode_re, '(\s+)~=(\s+)', '\g<1>!=\g<2>'],
	[mode_re, '(\s+)and(\s+)', '\g<1>&&\g<2>'],
	[mode_re, '(\s+)or(\s+)', '\g<1>||\g<2>'],
	[mode_re, '(\s+)not(\s+)', '\g<1>!\g<2>'],

	# # 统一先处理下空格更好匹配
	# [mode_re, '(\]\)\'\"])\s*(==|~=|and|or|not)\s*(\(\[\'\"])', '\g<1> \g<2> \g<3>'],
	# # 逻辑 == -> === ; ~= -> != ; and -> && ; or -> || ; not -> ! ;
	# [mode_re, '([\w\]\)\'\"])\s+==\s+([\w\(\[\'\"+-])', '\g<1> === \g<2>'],
	# [mode_re, '([\w\]\)\'\"])\s+~=\s+([\w\(\[\'\"+-])', '\g<1> != \g<2>'],
	# [mode_re, '([\w\]\)\'\"])\s+and\s+([\w\(\[\'\"+-])', '\g<1> && \g<2>'],
	# [mode_re, '([\w\]\)\'\"])\s+or\s+([\w\(\[\'\"+-])', '\g<1> || \g<2>'],
	# [mode_re, '([\s\(]+)not\s+([\w\(\[\'\"+-])', '\g<1>! \g<2>'],


	########## 语句 if for while ##########

	# 统一先处理下空格更好匹配
	[mode_re, '(?<=\W)(if|while|until)\(', '\g<1> ('],
	[mode_re, '\)(then|do)(?=\W)', ') \g<1>'],

	########## if ##########

	# lua : if ( condition ) then ... elseif ( condition ) then ... else ...end
	# js  : if (条件 1) { ... } else if (条件 2) { ... } else { ... }

	# 换行的else -> } else {
	[mode_re, '(?<=\n)( *)else *(?=\n)', '\g<1>}\n\g<1>else\n\g<1>{'],
	# 同上,不在开头的else
	[mode_re, '(?<=\n)( *)(\w.*?) +else *(?=\n)', '\g<1>\g<2>\n\g<1>}\n\g<1>else\n\g<1>{'],
	# 其他的else,不换行.上面两个替换之后都是(\n *else\n)的形式
	# [mode_re, '(?<=\W)else +(?=[^\n])', '} else { '],
	[mode_re, '(?<=\W)else(--|//| +)', '} else {\g<1>'],

	# if -> if (
	[mode_re, '(?<=\W)if\s+', 'if ('],
	# elseif -> } else if (
	[mode_re, '(?<=\n)( *)elseif\s+', '\g<1>}\n\g<1>else if ('],
	[mode_re, '(?<=\W)elseif\s+', '} else if ('],
	# then -> ) {
	[mode_re, '(?<=\n)( *)(\w.*\S) +then *(?=\n)', '\g<1>\g<2>)\n\g<1>{'],
	[mode_re, '(?<=\W)then(?=\W)', ') {'],

	# # if ( condition ) then -> if (condition) {
	# [mode_re, '(?<=\n)( *)if\s*\(\s*([\s\S]*?)\s*\)\s*then\s+',
	#     '\g<1>if (\g<2>)\n\g<1>{\n\g<1>    '],
	# # if condition then -> if (condition) { 不带括号的条件限制在一行内,否则容易配对错误
	# [mode_re, '(?<=\n)( *)if\s+([^(].*?)\s+then\s+',
	#     '\g<1>if (\g<2>)\n\g<1>{\n\g<1>    '],

	# # elseif ( condition ) then -> else if (condition) {
	# [mode_re, '(?<=\n)( *)elseif\s*\(\s*([\s\S]*?)\s*\)\s*then\s+',
	#     '\g<1>}\n\g<1>else if (\g<2>)\n\g<1>{\n\g<1>    '],
	# # 同上,不在开头的elseif,前面if转换之后的内部语句多了4个空格
	# [mode_re, '(?<=\n)    ( *)(\w.*?) +elseif\s*\(\s*([\s\S]*?)\s*\)\s*then\s+',
	#     '    \g<1>\g<2>\n\g<1>}\n\g<1>else if (\g<3>)\n\g<1>{\n\g<1>    '],
	# # elseif condition then -> else if (condition) { 不带括号的条件限制在一行内,否则容易配对错误
	# [mode_re, '(?<=\n)( *)elseif\s+(.*?)\s+then\s+',
	#     '\g<1>}\n\g<1>else if (\g<2>)\n\g<1>{\n\g<1>    '],
	# # 同上,不在开头的elseif,前面if转换之后的内部语句多了4个空格
	# [mode_re, '(?<=\n)    ( *)(\w.*?) +elseif\s+(.*?)\s+then\s+',
	#     '    \g<1>\g<2>\n\g<1>}\n\g<1>else if (\g<3>)\n\g<1>{\n\g<1>    '],


	# lua : 没有switch语句
	# js  : switch(n) { case 1: ... break; case 2: ... break; default: ... }

	########## for ##########

	# 注意: lua数组索引从1开始, js数组索引从0开始
	# lua : for init,max/min value, increment do ... end eg: for i=10,1,-1 do print(i) end
	# lua : for k , v in ipairs( jiaoZuiInfo) do ... end
	# js  : for (var i=0; i<5; i++) { ... }
	# js  : for (x in person) { txt=txt + person[x] }

	# for i=10,1,-1 do ... end -> for (var i=10; i>=1; i--) { ... }
	[mode_re, '(?<=\n)( *)for\s*([\w]*?)\s*=\s*(.+?)\s*,\s*(.+?)\s*,\s*-(.+?)\s+do',
		'\g<1>'+insert_descs['for']+'\n\g<1>for (var \g<2> = \g<3>; \g<2> >= \g<4>; \g<2> -= \g<5>)\n\g<1>{'],
	[mode_re, '(?<=\n)( *)for\s*([\w]*?)\s*=\s*(.+?)\s*,\s*(.+?)\s*,\s*(.+?)\s+do',
		'\g<1>'+insert_descs['for']+'\n\g<1>for (var \g<2> = \g<3>; \g<2> <= \g<4>; \g<2> += \g<5>)\n\g<1>{'],
	# for i=1,5 do ... end -> for (var i=0; i<=5; i++) { ... }
	[mode_re, '(?<=\n)( *)for\s*([\w]*?)\s*=\s*(.*?)\s*,\s*(.*?)\s+do',
		'\g<1>'+insert_descs['for']+'\n\g<1>for (var \g<2> = \g<3>; \g<2> <= \g<4>; \g<2>++)\n\g<1>{'],
	# for k , v in ipairs(...) do ... end -> for (var i=0; i<5; i++) { ... }
	[mode_re, '(?<=\n)( *)for\s*([\w]*?)\s*,\s*([\w]*?)\s*in\s*ipairs\s*\(\s*(.*?)\s*\)\s*do',
		'\g<1>for (var \g<2> = 0; \g<2> < \g<4>.length; \g<2>++)\n\g<1>{\n\g<1>    var \g<3> = \g<4>[\g<2>]'],
	# for k , v in pairs(...) do ... end -> for (x in ...) { ... }
	[mode_re, '(?<=\n)( *)for\s*([\w]*?)\s*,\s*([\w]*?)\s*in\s*pairs\s*\(\s*(.*?)\s*\)\s*do',
		'\g<1>for (var \g<2> in \g<4>)\n\g<1>{\n\g<1>    var \g<3> = \g<4>[\g<2>]'],


	########## while ##########

	# lua : while (condition) do statement(s) end
	# repeat statement(s) until( condition )
	# js  : while (i<5) { ... }
	# js  : do { ... } while (条件)

	# while -> while (
	[mode_re, '(?<=\W)while\s+', 'while ('],
	# do -> ) {
	[mode_re, '(?<=\n)( *)(\w.*\S)?(?(2) )+do *(?=\n)', '\g<1>\g<2>)\n\g<1>{'],
	[mode_re, '(?<=\W)do(?=\W)', ') {'],
	# repeat -> do {
	[mode_re, '(?<=\n)( *)repeat *(?=\n)', '\g<1>do\n\g<1>{'],
	[mode_re, '(?<=\W)repeat(?=\W)', 'do {'],
	# until ... -> } while ( ... )
	[mode_re, '(?<=\n)( *)until +(.+?) *(--|//|\n)', '\g<1>} while (\g<2>)\g<3>'],
	[mode_re, '(?<=\n)( *)(\w.*\S) +until +(.+?) *(--|//|\n)', '\g<1>\g<2> } while (\g<3>)\g<4>'],
	# [mode_re, '(?<=\n)( *)((\w.*\S)?)(?(3) )+until +(.+?) *(--|//|\n)', '\g<1>\g<2>} while (\g<4>)\g<5>'],

	# # while (...) do ... end -> while (...) { ... }
	# [mode_re, '(?<=\n)( *)while\s*\(\s*([\s\S]*?)\s*\)\s*do',
	#     '\g<1>while ( \g<2> )\n\g<1>{'],
	# # while ... do ... end -> while (...) { ... } 不带括号的条件限制在一行内,否则容易配对错误
	# [mode_re, '(?<=\n)( *)while\s+(.*?)\s+do',
	#     '\g<1>while ( \g<2> )\n\g<1>{'],
	# # repeat ... until(...) -> do { ... } while (...)
	# [mode_re, '(?<=\n)( *)repeat(\W)([\s\S]*?)(\W)until\s*\(',
	#     '\g<1>do\n\g<1>{\g<2>\g<3>\g<4>\n\g<1>} while ('],
	# # repeat ... until ... -> do { ... } while (...) 不带括号的条件限制在一行内,否则容易配对错误
	# [mode_re, '(?<=\n)( *)repeat(\W)([\s\S]*?)(\W)until\s+(.+?)\s*(--|//|\n)',
	#     '\g<1>do\n\g<1>{\g<2>\g<3>\g<4>\n\g<1>} while (\g<5>)\g<6>'],


	########## 关键词 ##########

	# nil -> undefined
	[mode_re, '(?<=\W)nil\s*(==|~=)', 'undefined \g<1>'],
	[mode_re, '(==|~=)\s*nil(?=\W)', '\g<1> undefined'],

	# 字符串拼接 .. -> +
	[mode_re, '([\w\]\)\'\"])\s*\.\.\s*([\w\(\[\'\"])', '\g<1> + \g<2>'],
	# 变量关键词 local -> var
	[mode_re, '(?<=\n)( *)local +(\w+) *,', '\g<1>'+insert_descs['local2']+'\n\g<1>var \g<2>,'],
	[mode_re, '(?<=\W)local +(\w+) *= *', 'var \g<1> = '],
	[mode_re, '(?<=\W)local +(\w+)(?=\W)', 'var \g<1>'],
	# sss = nil -> delete dic["b"]
	[mode_re, '(?<=\n)([\w\.\[\]\'\"]+) *= *nil(?=\W)', 'delete \g<1>'],
	# nil -> null
	[mode_re, '(?<=\W)nil(?=\W)', 'null'],
	# 关键词 self -> this (函数开头加了var self = this 这里就不要处理了)
	# [mode_re, '(?<=\W)self\.', 'this.'],


	########## lua函数 -> js函数 ##########

	# 数组长度 # -> .length
	# [mode_re, '#([a-zA-Z0-9_\.]+)', '\g<1>.length'],
	[mode_re, '# *([\w\.\[\]\'\"]+)', '\g<1>.length'],
	# table.insert(table, pos, value) -> arrayObject.splice(index,howmany,item1,.....,itemX)
	[mode_re, '(?<=\W)table.insert\s*\(\s*(.*?)\s*,\s*(\w.*?)\s*,\s*([\s\S]*?)\s*\)', '\g<1>.splice(\g<2>, 0, \g<3>)'],
	# table.insert(table, value) -> arrayObject.push(newelement1,newelement2,....,newelementX)
	[mode_re, '(?<=\W)table.insert\s*\(\s*(.*?)\s*,\s*([\s\S]*?)\s*\)', '\g<1>.push(\g<2>)'],
	# table.remove(table, pos) -> arrayObject.splice(index,1)
	[mode_re, '(?<=\W)table.remove\s*\(\s*(.*?)\s*,\s*(\w.*?)\s*\)', '\g<1>.splice(\g<2>, 1)'],
	# table.remove(table) -> arrayObject.pop()
	[mode_re, '(?<=\W)table.remove\s*\(\s*(.*?)\s*\)', '\g<1>.pop()'],
	# table.removebyvalue
	# table.sort(table, comp) -> arrayObject.sort(sortby)
	[mode_re, '(?<=\W)table.sort\s*\(\s*(.*?)\s*,\s*([\s\S]*?)\)', '\g<1>.sort(\g<2>)'],
	# table.indexof
	# table.nums(xxx) -> xxx.length
	[mode_re, '(?<=\W)table.nums *\( *([\w\.\[\]\'\"]+) *\)', '\g<1>.length'],
	# table.concat(table, sep,  start, end) -> arrayObject.join(separator)
	# concat含义不一致 arrayObject.concat(arrayX,arrayX,......,arrayX)

	# math.floor -> Math.floor
	[mode_re, '(?<=\W)math\.', 'Math.'],
	# print(...) -> log(...)
	[mode_re, '(?<=\W)print *\(', 'log('],
	# tostring -> String
	[mode_re, '(?<=\W)tostring *\(', 'String('],
	[mode_re, '(?<=\W)tonumber *\(', 'Number('],


	########## 自有函数 ##########

	# self:enableNodeEvents()
	[mode_re, '(?<=\n)(.*: *enableNodeEvents *\( *\))', '// \g<1>'],
	# onCleanup : function() -> cleanup : function()
	[mode_re, '(?<=\n)( *)onCleanup *: *function *\(', '\g<1>cleanup : function('],

	# Layer:createDarkLayer(180) -> cc.LayerColor.create(cc.c4b(0, 0, 0, 180))
	[mode_re, '(?<=\W)Layer:createDarkLayer *\( *(\d*?) *\) *', 'cc.LayerColor.create(cc.c4b(0, 0, 0, \g<1>))'],
	# [mode_s, 'ccui.ImageView:create(', 'Sprite.createSpriteWithPlist('],    # 临时修改

	# 重新封装的函数
	[mode_re, '(?<=\W)cc\.Sprite:create *\(', 'Sprite.createSpriteWithPlist('],


	# 特殊扩展函数
	[mode_re, ':setOpacity\(', '.opacityEx('],
	[mode_re, ':(addTo|zOrder|scaleX|scaleY|scale|rotation|skewX|skewY|anchor|contentSize|position|positionX|positionY|tag|opacity|color|getPositionByLayout|layout|getPositionByScreenLayout|layoutScreen)\(', '.\g<1>Ex('],
	# 普通函数 : -> . 注意成员函数的形式: function(
	[mode_re, ':(\w+?) *\(', '.\g<1>('],


	########## 资源路径,需生成合图,在Resource.js中添加 ##########

	# ImageLoader.createSpriteWithImageName("...")
	[mode_re, '(?<=\W)ImageLoader.createSpriteWithImageName\( *\"(.+?)\.png\" *\)',
		'Sprite.createSpriteWithPlist(res.mj_res_plist, \"mj/\g<1>.png\")'],
	[mode_re, '(?<=\W)ImageLoader.createSpriteWithImageName\( *(.+?) *\)',
		'Sprite.createSpriteWithPlist(res.mj_res_plist, \g<1>)'],
	# ImageLoader.createScale9SpriteWithImageName("table/tips_bg.png")
	[mode_re, '(?<=\W)ImageLoader.createScale9SpriteWithImageName\( *\"(.+?)\.png\" *\)',
		'Scale9Sprite.createWithPlist(res.mj_res_plist, \"mj/\g<1>.png\")'],
	[mode_re, '(?<=\W)ImageLoader.createScale9SpriteWithImageName\( *(.+?) *\)',
		'Scale9Sprite.createWithPlist(res.mj_res_plist, \g<1>)'],

	# "games/mj_common/images/over_layer/info_effect_hz.png"
	[mode_re, '\( *\"games/mj_common/images/(.+?)\.png\" *\)', '(res.mj_res_plist, \"mj/\g<1>.png\")'],
	# "games/guiy/images/huType/info_hp_dh.png"
	[mode_re, '\( *\"games/([\w]+?)/images/(.+?)\.png\" *\)', '(res.\g<1>_plist, \"\g<1>/\g<2>.png\")'],
	# ("games/area_guiyang/common/images/info_effect_bg.png") -> (res.area_guiyang_plist, "area_guiyang/info_effect_bg.png")
	[mode_re, '\( *\"games/([\w]+?)/common/images/([\w]+?)\.png\" *\)', '(res.\g<1>_plist, \"\g<1>/\g<2>.png\")'],
	# 还有一些变量或者字符串拼接的图片路径手动修改


	# 多行注释 --[==[ 和 --]==]
	[mode_re, '--\[=?\[', '/*'],
	[mode_re, '\]=?\]', '*/'],
	# 单行注释(必须先处理多行注释)
	[mode_s, '--', '//'],
]


####################

def convert_string(fileName, buf):
	# 增加一个换行,以免文件开头匹配不到
	buf = '\n'+buf

	# # 缩进2格改4格 如果只有少量2个空格缩进的就不要用了
	# match = re.search('\n(\ {2})([\w]+?)', buf)
	# if match:
	#     buf = re.sub('\n([\ \t]+?)([\S])', '\n\g<1>\g<1>\g<2>', buf)

	########## 各种查找替换 ##########

	for k, config in enumerate(config_replace):
		# print(k, config)
		if config[0] == mode_s:
			buf = buf.replace(config[1], config[2])
		elif config[0] == mode_re:
			buf = re.sub(config[1], config[2], buf)

	########## 处理缩进 ##########

	# 增加一个缩进
	buf = re.sub('\n(.+?)', '\n    \g<1>', buf)

	return buf

def convert_lua_2_js(file_src, file_dst):
	# print(file_src, file_dst)

	# 读文件
	fp = open(file_src, 'rb')
	buf = fp.read()
	fp.close()

	(filepath,tempfilename) = os.path.split(file_dst);
	(fileName, suffix) = os.path.splitext(tempfilename)

	# 构造函数继承 local M = class("Shake",function ( ) return cc.ActionInterval end)
	match = re.search('\nlocal\s+(\w+)\s*=\s*class\s*\(\s*\"(\S+?)\"\s*,\s*function\s*\(([\s\S]*?)end\)', buf)
	if match:
		# print(match.group(0))
		buf.replace(match.group(0), '\n//*\n'+match.group(0)+'\n*//')

	# 类继承的形式 class ctor eg: local M = class("GYFinishLayer", cc.Layer)
	extendClass = ''
	ctorParams = ''
	match = re.search('local\s+(\w+)\s*=\s*class\s*\(\s*\"(\S+?)\"\s*,\s*(\S+?)\s*\)', buf)
	if match:
		extendClass = match.group(3)
		# ctor参数 function M:ctor(...)
		match = re.search('(?<=\n)( *)function\s+([\w]+?):ctor *\(([\s\S]*?)\)', buf)
		if match:
			ctorParams = match.group(3)

	# 写文件
	fp = open(file_dst, 'wb')
	fline(fp)
	fwriteline(fp, "\"use strict\"")
	fline(fp)
	# 继承类的形式
	if len(extendClass) > 0:
		fwriteline(fp, "var %s = %s.extend(\n{" % (fileName, extendClass))
		fwriteline(fp, convert_string(fileName, buf))
		fwriteline(fp, "})")

		# 添加create函数
		fwriteline(fp, "\n%s.create = function(%s)" % (fileName, ctorParams))
		fwriteline(fp, "{")
		fwriteline(fp, "    return new %s(%s)" % (fileName, ctorParams))
		fwriteline(fp, "}")

	# 普通的形式
	else:
		fwriteline(fp, "var %s = \n{" % fileName)
		fwriteline(fp, convert_string(fileName, buf))
		fwriteline(fp, "}")
	fp.close()
	print "%s has dump done !" % fileName

####################

def fwrite(fp, s, *args):
	if len(args) > 0:
		tnum = args[0]
		if tab_size_dst >= 2:
			for i in range(0, tnum):
				for j in range(0, tab_size_dst):
					fp.write(" ")
		else:
			for i in range(0, tnum):
				fp.write("\t")
	fp.write(s)

def fwriteline(fp, s, *args):
	fwrite(fp, s, *args)
	fp.write("\n")

def fline(fp, *args):
	nnum = 1
	if len(args) > 0:
		nnum = args[0]
	for i in range(0, nnum):
		fp.write("\n")

Iterative(src_path)
