import jieba
import jieba.posseg as psg
import regex as re
import json

def get_key(dict, value):
    return [k for k, v in dict.items() if v == value]

def GetPOS(input_string):
    # 将输入字符串进行词性标注
    #print("用户输入为：",input_string)
    #print('='*100)
    seg = jieba.posseg.cut(input_string)
    pos_list = []
    for i in seg:
        pos_list.append((i.word, i.flag))
    #print("词性标注结果为：",pos_list)
    #print('=' * 100)
    return pos_list


def IdentQuery(for_query_entry_judge_set):
    # 根据词性标注的结果中是否含有num和m，判断是否需要进行组合查询识别,若含有更新查询标识为1
    # 若组合查询标识为1，则进入组合查询识别阶段,否则进入关键词查询
    query_sign = 0

    if 'bf' in for_query_entry_judge_set or 'm' in for_query_entry_judge_set or 'num' in for_query_entry_judge_set:
        query_sign = 1
    else:
        print("无法识别组合查询语句，请使用关键词搜索！")
    return query_sign

def GetValue(input_string,pos_list,for_query_entry_judge_set):
    # 解析value值
    # 分为两种情况，根据词性标注和根据正则表达式，收益率的6个月涨幅和12个月涨幅用正则表达式会把6和12解析为value，所以用词性标注为bf的直接识别为value值，而锁定期 起购金额等，带单位，需要识别出万、年、天
    # 月等词，用正则表达式匹配

    pos_dict = dict(pos_list)
    num_list = get_key(pos_dict, 'bf')
    if 'bf' in for_query_entry_judge_set:
        att_value = num_list[0]
    else:
        rule = u"((\\d+)(\.)(\\d+)%)|((\\d+)%)|(百分之[一二三四五六七八九十])|(((\\d+|[一二三四五六七八九十]?[一二三四五六七八九十])天)|((\\d+|[一二三四五六七八九十])年)|((\\d+|[一二三四五六七八九十])个?月)(?!涨幅)|((\\d+|[一二三四五六七八九十])(百|千|十)?万)|((\\d+)(\.)(\\d+))|(\\d+))"

        pattern = re.compile(rule)
        match = pattern.search(input_string)

        if match is not None:
            att_value = match.group()

    #print("解析字段值att_value为:", att_value)
    #print('='*100)
    return att_value

def GetAttrName(att_value,for_query_entry_judge_set):

    # 识别字段名attr_name,如果有字段名字段直接提取，若没有根据value判断
    attr_name_set = {'rate', 'qrate', 'yrate', 'srate', 'wrate', 'lrate', 'nrate', 'period', 'lockperiod', 'minamount','interestrate'}
    attr_name_t = for_query_entry_judge_set & attr_name_set
    attr_name = set()
    if attr_name_t:
        attr_name = attr_name_t
    else:
        if '%' in att_value:
            attr_name = {'rate'}
        elif '天' in att_value or '月' in att_value or '年' in att_value:
            attr_name = {'period', 'lockperiod'}
        elif '万' in att_value:
            attr_name = {'minamount'}
    #print(attr_name)
    return attr_name

    # if query_sign ==1:
    # 1）解析value值
    # 2）识别字段名
    # 3）识别产品类别
    # 4）识别关系词
def GetPrdType(for_query_entry_judge_set,attr_name):

    # 确定产品类型prd_type,如果有产品类型直接提取，若没有根据attr_name判断
    prd_type_set = {'allprd', 'finan', 'fund', 'debtfund','deposit'}
    finan_char = {'period', 'yrate'}
    fund_char = {'lockperiod', 'qrate', 'wrate'}
    debtfund_char = {'srate', 'lrate', 'nrate'}
    deposit_char = {'interestrate'}

    prd_type_t = prd_type_set & for_query_entry_judge_set

    prd_type = {'allprd'}
    if prd_type_t and 'allprd' not in prd_type_t:
        prd_type = prd_type_t
    else:
        if attr_name.issubset(finan_char) :
            prd_type = {'finan'}

        elif attr_name.issubset(fund_char):
            prd_type = {'fund'}
        elif attr_name.issubset(debtfund_char):
            prd_type = {'debtfund'}
        elif attr_name.issubset(deposit_char):
            prd_type = {'deposit'}

    name_prdtype = {'finan': ['period', 'yrate'], 'fund': ['lockperiod', 'qrate', 'wrate'],
                    'debtfund': ['srate', 'lrate', 'nrate']}
    attr_name_judge = {'period','lockperiod'}
    if prd_type != {'allprd'} and attr_name & attr_name_judge:
        for m in prd_type:
            if set(name_prdtype[m]) & attr_name:
                attr_name = set(name_prdtype[m]) & attr_name

    #print(prd_type)
    return prd_type,attr_name

def GetRelatSign(for_query_entry_judge_set):

    # 确定关系词
    relat_set = {'eql', 'lt', 'gt', 'lte', 'gte'}
    relat_set_t = relat_set & for_query_entry_judge_set
    relat = ''
    if relat_set_t:
        relat = list(relat_set_t)[0]
    return relat

def GetOrg(pos_list):
    #识别机构名称，若没有机构名称，默认为所有机构
    for_query_entry_judge_set = set([x[1] for x in pos_list])
    org_sign = 'allorg'
    if 'org' in for_query_entry_judge_set:
        org_sign = get_key(dict(pos_list), 'org')
        org_sign = ','.join(org_sign)
    return org_sign

def Normalization(att_value,attr_name,prd_type,relat,org_sign):
    # 将rate字段规范成数据库字段，定义对应关系字典
    databs_att_dic = {'rate': 'RATE', 'qrate': 'RATE', 'yrate': 'RATE', 'srate': 'RATE', 'wrate': 'RATE2',
                      'lrate': 'RATE2', 'nrate': 'RATE3', 'period': 'PERIOD', 'minamount': 'MIN_AMOUNT',
                      'lockperiod': 'LOCKPERIOD','interestrate':'RATE'}
    databs_prdtype_dic = {'allprd': '1,2,3,4', 'finan': 2, 'fund': 1, 'debtfund': 3,'deposit':4}
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

    # 将识别的结果转成字典，再将字典转成json
    result = {"att_value": att_value, "att_name": list(attr_name_db), "relat_sign": relat,
              "prd_type": list(prd_type_db),"org":org_sign}

    #json_dic = json.dumps(result, indent=4, ensure_ascii=False)

    #print('=' * 80)
    #print(result)
    return result

def OrgNAPTopp(attr_name,prd_type,sign):
    # 字段名与产品类型矛盾判断，根据定义冲突字典实现
    #print("检测查询字段名称是否与产品类型冲突...")
    if 'allprd' in prd_type:
        sign = 0
    else:
        name_opp_prdtype = {'lockperiod': ['finan', 'debtfund'], 'period': ['fund', 'debtfund'],
                            'srate': ['fund', 'finan'],
                            'lrate': ['fund', 'finan'], 'wrate': ['finan', 'debtfund'],
                            'qrate_opp': ['finan', 'debtfund'],
                            'yrate': ['fund', 'debtfund']}
        name_prdtype = {'finan': ['period', 'yrate'], 'fund': ['lockperiod', 'qrate', 'wrate'],
                        'debtfund': ['srate', 'lrate', 'nrate']}

        for m in prd_type:
            if set(name_prdtype[m]) & attr_name:
                sign = 0
            else:
                for x in attr_name:
                    if x in name_opp_prdtype.keys():
                        prd_opp = name_opp_prdtype[x]
                        if m in prd_opp:
                            sign = 1
                            print('查询关键词（%s）与产品类型（%s）冲突！请重新输入' % (x, m))
    return sign

def OrgNAVAopp(attr_name,att_value,sign):
    # 字段名与字段值矛盾判断,通过正则表达式实现
    #print("检测查询字段名称是否与字段值冲突...")
    rate_list = ['rate', 'srate', 'lrate', 'nrate', 'yrate', 'wrate', 'qrate','interestrate']
    peri_list = ['period', 'lockperiod']
    amin_list = ['minamount']

    rate_opp_rule = u"((\\d+|[一二三四五六七八九十]?[一二三四五六七八九十])天)|((\\d+|[一二三四五六七八九十])年)|((\\d+|[一二三四五六七八九十])个?月)|((\\d+|[一二三四五六七八九十])(百|千|十)?万)"

    period_opp_rule = u"((\\d+)(\.)(\\d+)%)|((\\d+)%)|((\\d+|[一二三四五六七八九十])(百|千|十)?万)|((\\d+)(\.)(\\d+))"

    amint_opp_rule = u"((\\d+)(\.)(\\d+)%)|((\\d+)%)|((\\d+|[一二三四五六七八九十]?[一二三四五六七八九十])天)|((\\d+|[一二三四五六七八九十])年)|((\\d+|[一二三四五六七八九十])个?月)"

    for x in attr_name:
        if x in rate_list:
            pattern = re.compile(rate_opp_rule)
            match = pattern.search(att_value)

            if match is not None:
                sign = 1
                print("查询关键词（%s）与属性值（%s）冲突！请重新输入" % (x, att_value))
        elif x in peri_list:
            pattern = re.compile(period_opp_rule)
            match = pattern.search(att_value)

            if match is not None:
                sign = 1
                print("查询关键词（%s）与属性值（%s）冲突！请重新输入" % (x, att_value))

        elif x in amin_list:
            pattern = re.compile(amint_opp_rule)
            match = pattern.search(att_value)

            if match is not None:
                sign = 1
                print("查询关键词（%s）与属性值（%s）冲突！请重新输入" % (x, att_value))
    return sign


    # 如果att_name为空，则为整数为全部字段，如果为小数，则为收益率或者起购金额

    # 字段名称与产品类型矛盾的处理，如字段名为锁定期，产品类型为理财产品，而只有货币基金才有锁定期，这就矛盾了，需要做判断

    # 字段名称与字段值矛盾的处理，如收益率大于30天的产品

    # 省略关系词的情况 自动补充：百分数为大于等于，起购金额大于等于，锁定期小于等于，理财期限等于

    # 数字解析：2万解析为20000

#输入单关键词查询语句，解析成json结构体
def SingleQueryAna(pos_list):
    #pos_list = GetPOS(input_string)
    input_string = [x[0] for x in pos_list]
    input_string =''.join(input_string)
    for_query_entry_judge_set = set([x[1] for x in pos_list])
    que_sign = IdentQuery(for_query_entry_judge_set)

    if que_sign:
        a_val = GetValue(input_string, pos_list, for_query_entry_judge_set)
        a_name = GetAttrName(a_val, for_query_entry_judge_set)
        p_type,a_name = GetPrdType(for_query_entry_judge_set, a_name)
        re_sign = GetRelatSign(for_query_entry_judge_set)
        sign = 0
        sign_np = OrgNAPTopp(a_name, p_type, sign)
        sign_nv = OrgNAVAopp(a_name, a_val, sign)
        result = 0
        org_sign = GetOrg(pos_list)
        #print(org_sign)
        if sign_np == 0 and sign_nv == 0:
            # print("检测完成，没有发现冲突！")
            # 判断att_name和relat_sign是否为空，若为空，返回提示语，提示用户补全查询信息
            if re_sign:
                if a_name:
                    # 将识别的结果转成字典，再将字典转成json
                    result = Normalization(a_val, a_name, p_type, re_sign,org_sign)
                else:
                    print("请补全查询关键词！")
            else:
                print("请补全查询逻辑比较词！")
        return result

#统计词性标注的结果与对应的字段类型匹配的个数
def getValueCount(list,value_set):
    list_value =[x[1] for x in list]
    count = 0
    for x in list_value:
        if x in value_set:
            count = count +1
    return count

#判断查询为多关键词还是单关键词查询,本程序默认关键词不能省略，若省略关键词，提示用户补全查询信息,若mut=1则为单关键词查询，若为2则为多关键词查询
def JudgeMuSingle(pos_list):
    for_query_entry_judge_set = set([x[1] for x in pos_list])
    attr_name_set = {'rate', 'qrate', 'yrate', 'srate', 'wrate', 'lrate', 'nrate', 'period', 'lockperiod', 'minamount'}
    attr_name_t = for_query_entry_judge_set & attr_name_set
    #print(attr_name_t)

    att_value_set = {'num', 'bf','m'}
    att_value_t = getValueCount(pos_list, att_value_set)
    #print(att_value_t)
    if len(attr_name_t) <= 1 and att_value_t == 1:
        mut = 1
    elif len(attr_name_t) > 1 or att_value_t > 1:
        # 判断为多关键字查询
        if len(attr_name_t) <= att_value_t:

            mut = 2
        else:
            mut = 3
            print("请补全查询信息！")
    # else:
    # 暂时判断为单关键词查询，后面如果增加单关键词的多条件查询可以细分，暂时先不区分，后面增加了后可以增加mut的类型，不只有0和1
    return mut

#识别布尔逻辑词
def OrgnBool(input_string):
    boolean = 'or'
    rule_or = u"[和且]"
    pattern_or = re.compile(rule_or)
    match_or = pattern_or.search(input_string)

    if match_or is not None:
        boolean = 'and'
    return boolean

#将多关键词查询语句切分成多个单一关键词查询语句
def SplitQuery(input_string,pos_list):
    attr_name_set = {'rate', 'qrate', 'yrate', 'srate', 'wrate', 'lrate', 'nrate', 'period', 'lockperiod', 'minamount'}
    attr_rela_set = {'eql', 'lt', 'gt', 'lte', 'gte'}
    rule_split = u"[或和且，、 ,]"
    pattern_split = re.compile(rule_split)
    match_split = pattern_split.split(input_string)
    query_list = []

    if len(match_split) != 1:
        #print(match_split)
        mut_query_list = match_split
        for x in mut_query_list:
            ##待增加：被正则表达式分割后的元素中扔包含多关键词查询，需要进一步拆分
            pos_x = GetPOS(x)
            query_list.append(pos_x)

        # 下面是将mut_query_list中的每个元素进行单关键词查询语句的解析
    else:
        pos_list_split = pos_list
        j = 0
        for i in range(2, len(pos_list_split)):
            if pos_list_split[i][1] in attr_name_set:
                # print(i)
                query_str1 = pos_list_split[j:i]
                query_list.append(query_str1)
                # print("单查询：", query_list)
                # print(query_str1)
                j = i

            elif pos_list_split[i-1][1] not in attr_name_set and pos_list_split[i][1] in attr_rela_set:
                quer_str = pos_list_split[j:i]
                query_list.append(quer_str)
                #print("单查询：", query_list)
                #print(quer_str)
                j = i
        query_list.append(pos_list_split[j:])

    #print(query_list)
    return query_list

#单关键词查询间是否矛盾查询，主要指and的情况，主要指产品类型，or的情况不做判断
def JudgeContra(json_l,boolen_s):
    if boolen_s == 'or':
        json_l = json_l
    else:
        prd_set = set([1,2,3])
        for dic in json_l:
            d_prd = set(dic['prd_type'])
            prd_set = prd_set & d_prd
            if prd_set == set():

                print("查询语句间有矛盾！")
                break
        if prd_set != set():
            for dic in json_l:
                dic['prd_type'] = list(prd_set)
        else:
            json_l = []

    return json_l

#组合查询主函数
def GetResult(text):
    #text = "锁定期小于3天"
    pos_list = GetPOS(text)
    print(text)
    print(pos_list)

    # 判断为单关键词查询还是多关键词查询
    mut_sign = JudgeMuSingle(pos_list)
    json_dic = {}
    # print("*" * 200)
    if mut_sign == 1:
        result = SingleQueryAna(pos_list)
        json_dic = json.dumps(result, indent=4, ensure_ascii=False)
        #print(json_dic)
        # print(resu)
    elif mut_sign == 2:
        # 判断boolen
        boolen_sign = OrgnBool(text)

        #print(boolen_sign)
        que_list = SplitQuery(text, pos_list)
        #北京银行收益率大于5%锁定期小于1天的产品，机构‘北京银行’在分割后只在第一个查询语句中，但实际的语义第二个也包含，需要给第二个句子补全机构信息
        #收益率大于5%，北京银行锁定期小于1天的产品，此种情况不需要给第一个句子补全
        #暂不增加

        json_list = []
        for que in que_list:
            que_json = SingleQueryAna(que)
            json_list.append(que_json)
            json_list = JudgeContra(json_list,boolen_sign)
        # 将结果拼成json结构
        json_list = [x for x in json_list if x!=0]
        json_list = [x for x in json_list if x!=None]
        #对‘收益率大于4%小于6%的产品’逻辑词的更正
        #询语句中不包含‘且’，但其含义是‘且’，判断方法为补全单关键词查询的att_name后，多个单关键词查询的att_name相同，则将逻辑词识别为and
        att_name_list = set(["".join(x['att_name']) for x in json_list])
        if len(att_name_list) ==1:
            boolen_sign = 'and'
        #
        result = dict()
        if len(json_list)>1:
            if boolen_sign == 'and':
                result['must'] = json_list
            else:
                result['should'] = json_list
        else:
            if len(json_list) != 0:
                result = json_list[0]
            else:
                result = dict()
        json_dic = json.dumps(result, indent=4, ensure_ascii=False)

        #print(json_dic)
    return json_dic


if __name__ == "__main__":
    # 结巴分词词典加载
    word_dic_file = 'dict.txt'
    jieba.load_userdict(word_dic_file)  # 添加自定义词库
    text = "北京银行收益率大于3%锁定期小于1天的产品"
    output = GetResult(text)
    if output:
        print(output)