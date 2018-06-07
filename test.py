import jieba
import jieba.posseg as psg
import regex as re
import json

#注意：为了修复词性标注将百分数的数字和百分号分开，修改了源码：C:\Users\liuhy\AppData\Local\Programs\Python\Python36\Lib\site-packages\jieba\posseg\_init_.py

# 结巴分词词典加载
word_dic_file = 'dict.txt'
jieba.load_userdict(word_dic_file)  # 添加自定义词库

#将输入字符串进行词性标注
input_string = "锁定期大于3%的纯债"
print(input_string)
seg = jieba.posseg.cut(input_string)
pos_list = []
for i in seg:
    pos_list.append((i.word, i.flag))
print(pos_list)
#根据词性标注的结果中是否含有num和m，判断是否需要进行组合查询识别,若含有更新查询标识为1
query_sign = 0
for_query_entry_judge_set = set([x[1] for x in pos_list])
if 'num' in for_query_entry_judge_set or 'm' in for_query_entry_judge_set or 'bf' in for_query_entry_judge_set:
    query_sign = 1
else:
    print("无法识别组合查询语句，请使用关键词搜索！")

#若组合查询标识为1，则进入组合查询识别阶段


#if query_sign ==1:
    #1）解析value值
    #2）识别字段名
    #3）识别产品类别
    #4）识别关系词

#解析value值
#分为两种情况，根据词性标注和根据正则表达式，收益率的6个月涨幅和12个月涨幅用正则表达式会把6和12解析为value，所以用词性标注为bf的直接识别为value值，而锁定期 起购金额等，带单位，需要识别出万、年、天
#月等词，用正则表达式匹配
def get_key(dict, value):
    return [k for k, v in dict.items() if v == value]
pos_dict = dict(pos_list)
num_list = get_key(pos_dict,'bf')
if 'bf' in for_query_entry_judge_set:
    att_value = num_list[0]
else:
    rule = u"((\\d+)(\.)(\\d+)%)|((\\d+)%)|(((\\d+|[一二三四五六七八九十]?[一二三四五六七八九十])天)|((\\d+|[一二三四五六七八九十])年)|((\\d+|[一二三四五六七八九十])个?月)(?!涨幅)|((\\d+|[一二三四五六七八九十])(百|千|十)?万)|((\\d+)(\.)(\\d+))|(\\d+))"

    pattern = re.compile(rule)
    match = pattern.search(input_string)

    if match is not None:
        att_value = match.group()

print("att_value:",att_value)

#识别字段名attr_name,如果有字段名字段直接提取，若没有根据value判断
attr_name_set = {'rate','qrate','yrate','srate','wrate','lrate','nrate','period','lockperiod','minamount'}
attr_name_t = for_query_entry_judge_set & attr_name_set
attr_name = set()
if attr_name_t:
    attr_name =attr_name_t
else:
    if '%' in att_value :
        attr_name = {'rate'}
    elif '天' in att_value or '月' in att_value or '年' in att_value:
        attr_name = {'period','lockperiod'}
    elif '万' in att_value:
        attr_name ={'minamount'}


#确定产品类型prd_type,如果有产品类型直接提取，若没有根据attr_name判断
prd_type_set = {'allprd','finan','fund','debtfund'}
finan_char = {'period','yrate'}
fund_char = {'lockperiod','qrate','wrate'}
debtfund_char = {'srate','lrate','nrate'}

prd_type_t = prd_type_set & for_query_entry_judge_set

prd_type = {'allprd'}
if prd_type_t and 'allprd' not in prd_type_t:
    prd_type = prd_type_t
else:
    if attr_name &finan_char:
        prd_type = {'finan'}

    elif attr_name & fund_char:
        prd_type ={'fund'}
    elif attr_name & debtfund_char:
        prd_type ={'debtfund'}

#确定关系词
relat_set = {'eql','lt','gt','lte','gte'}
relat_set_t = relat_set & for_query_entry_judge_set
relat = ''
if relat_set_t:
    relat = list(relat_set_t)[0]

#将rate字段规范成数据库字段，定义对应关系字典
databs_att_dic = {'rate':'RATE','qrate':'RATE','yrate':'RATE','srate':'RATE','wrate':'RATE2','lrate':'RATE2','nrate':'RATE3','period':'PERIOD','minamount':'MIN_AMOUNT','lockperiod':'LOCKPERIOD'}
databs_prdtype_dic = {'allprd':'1,2,3','finan':2,'fund':1,'debtfund':3}
attr_name_db = set()
for x in attr_name:
    y = databs_att_dic[x]
    attr_name_db.add(y)
prd_type_db = set()
for x in prd_type:

    y = databs_prdtype_dic[x]
    if isinstance(y, str):
        if ',' in y:
            xs = y.split(',')
            xs = [int(x) for x in xs]
            prd_type_db = set(xs)
    else:
        prd_type_db.add(y)

#字段名与产品类型矛盾判断，根据定义冲突字典实现
name_opp_prdtype = {'lockperiod':['finan','debtfund'],'period':['fund','debtfund'],'srate':['fund','finan'],'lrate':['fund','finan'],'wrate':['finan','debtfund'],'qrate_opp':['finan','debtfund'],'yrate':['fund','debtfund']}

for x in attr_name:
    if x in name_opp_prdtype.keys():
        prd_opp = name_opp_prdtype[x]
        for y in prd_type:
            if y in prd_opp:
                print('查询关键词（%s）与产品类型（%s）冲突！请重新输入'%(x,y))

#字段名与字段值矛盾判断,通过正则表达式实现
rate_list = ['rate','srate','lrate','nrate','yrate','wrate','qrate']
peri_list = ['period','lockperiod']
amin_list = ['minamount']

rate_opp_rule = u"((\\d+|[一二三四五六七八九十]?[一二三四五六七八九十])天)|((\\d+|[一二三四五六七八九十])年)|((\\d+|[一二三四五六七八九十])个?月)|((\\d+|[一二三四五六七八九十])(百|千|十)?万)"

period_opp_rule = u"((\\d+)(\.)(\\d+)%)|((\\d+)%)|((\\d+|[一二三四五六七八九十])(百|千|十)?万)|((\\d+)(\.)(\\d+))"

amint_opp_rule = u"((\\d+)(\.)(\\d+)%)|((\\d+)%)|(((\\d+|[一二三四五六七八九十]?[一二三四五六七八九十])天)|((\\d+|[一二三四五六七八九十])年)|((\\d+|[一二三四五六七八九十])个?月)"

for x in attr_name:
    if x in rate_list:
        pattern = re.compile(rate_opp_rule)
        match = pattern.search(att_value)

        if match is not None:
            print("查询关键词（%s）与属性值（%s）冲突！请重新输入"%(x,att_value))
    elif x in peri_list:
        pattern = re.compile(period_opp_rule)
        match = pattern.search(att_value)

        if match is not None:
            print("查询关键词（%s）与属性值（%s）冲突！请重新输入" % (x, att_value))

    elif x in amin_list:
        pattern = re.compile(amint_opp_rule)
        match = pattern.search(att_value)

        if match is not None:
            print("查询关键词（%s）与属性值（%s）冲突！请重新输入" % (x, att_value))



#判断att_name和relat_sign是否为空，若为空，返回提示语，提示用户补全查询信息
if relat:
    if  attr_name:
        # 将识别的结果转成字典，再将字典转成json
        result = {"att_value:": att_value, "att_name:": list(attr_name_db), "relat_sign:": relat,
                  "prd_type:": list(prd_type_db)}

        json_dic = json.dumps(result, indent=4, ensure_ascii=False)

        print('=' * 100)
        print(json_dic)

    else:
        print("请补全查询关键词！")
else:
    print("请补全查询逻辑比较词！")



'''
print("att_value:",att_value)
print("att_name:",attr_name_db)
print("relat_sign:",relat)
print("prd_type:",prd_type_db)
'''
##如果att_name为空，提示用户补全信息（则为整数为全部字段，如果为小数，则为收益率或者起购金额）

##字段名称与产品类型矛盾的处理，如字段名为锁定期，产品类型为理财产品，而只有货币基金才有锁定期，这就矛盾了，需要做判断

#字段名称与字段值矛盾的处理，如收益率大于30天的产品

##省略关系词的情况 ，提示用户补全信息（自动补充：百分数为大于等于，起购金额大于等于，锁定期小于等于，理财期限等于）

#数字解析：2万解析为20000