from __future__ import unicode_literals # compatible with python3 unicode coding
import jieba
import jieba.posseg as psg
from deepnlp import nn_parser
import sys
sys.path.append('D:/liuhy/语音搜索/组合查询/HuanNLP-master')  #加入路径，添加目录
import huannlp

def getParse(input_string,parser):


    # 结巴分词词典加载
    word_dic_file = 'dict_parse.txt'
    jieba.load_userdict(word_dic_file)  # 添加自定义词库

    # 将输入字符串进行词性标注


    print(input_string)
    seg = jieba.posseg.cut(input_string)
    pos_list = []
    for i in seg:
        pos_list.append((i.word, i.flag))
    print(pos_list)

    words = [x[0] for x in pos_list]
    tags = [x[1] for x in pos_list]

    # Example 1, Input Words and Tags Both
    # words = ['它', '熟悉', '一个', '民族', '的', '历史']
    # tags = ['r', 'v', 'm', 'n', 'u', 'n']

    # Parsing
    dep_tree = parser.predict(words, tags)

    # Fetch result from Transition Namedtuple
    num_token = dep_tree.count()
    print("id\tword\tpos\thead\tlabel")
    for i in range(num_token):
        cur_id = int(dep_tree.tree[i + 1].id)
        cur_form = str(dep_tree.tree[i + 1].form)
        cur_pos = str(dep_tree.tree[i + 1].pos)
        cur_head = str(dep_tree.tree[i + 1].head)
        cur_label = str(dep_tree.tree[i + 1].deprel)
        print("%d\t%s\t%s\t%s\t%s" % (cur_id, cur_form, cur_pos, cur_head, cur_label))
    return cur_label

def getParse2(text):
    # 结巴分词词典加载
    word_dic_file = 'dict_parse.txt'
    jieba.load_userdict(word_dic_file)  # 添加自定义词库

    # 将输入字符串进行词性标注

    print(text)
    seg = jieba.posseg.cut(text)
    pos_list = []
    for i in seg:
        pos_list.append((i.word, i.flag))
    print(pos_list)

    words = [x[0] for x in pos_list]
    tags = [x[1] for x in pos_list]

    nlp = huannlp.HuanNLP('CRF')
    # text = '一是新类型性能灌注树脂的创新开发;'
    #words = nlp.cut(text)
    #print('words', words)
    #postags = nlp.postag(words)
    #print('postags', postags)
    #ners = nlp.ner(text)
    #print('ners', ners)
    deps = nlp.dep(words, tags)
    print("="*100)
    for x in deps:
        print(x)
    #print('deps', deps)
    return deps

#string1 =  "锁定期大于3天、收益率大于5%的产品"
string2 =  "锁定期和理财期限小于30天"
r = getParse2(string2)
parser = nn_parser.load_model(name='zh')
#r1 = getParse(string,parser)
#r2 = getParse(string1,parser)
r3 = getParse(string2,parser)

#支持的类型
#万份收益大于1.3或锁定期大于3天的产品
#万份收益大于1.3和锁定期大于3天的产品
#锁定期大于1.3 收益率大于3天的产品
#锁定期大于1.3，收益率大于3天的产品

#不支持的类型（分析错误）
#万份收益大于1.3、锁定期大于3天的产品
#万份收益大于1.3，锁定期大于3天的产品
#万份收益大于1.3 锁定期大于3天的产品
#锁定期大于1.3、收益率大于3天的产品

#不支持的类型（跑不出结果)
#万份收益大于1.3、锁定期大于3天、理财期限小于30天的产品