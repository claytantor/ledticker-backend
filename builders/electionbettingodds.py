import requests

from lxml import etree, html

from senders import FlashlexMessageSender

def next_president(builder_config, sender_config, cache, tz):
    page = requests.get(builder_config['data_url'])
    tree = html.fromstring(page.content)

    tables = tree.xpath('//div[@class="container"]/table')
    
    for i in range(len(tables)):
        items = handleRaceTable(tables[i])
        # print(i, items)
        if(len(items)>0):
            # print(items)

            for item in items:
                messageModel = {
                    'body':'{0}|{1}|{2}'.format("President 2020", item['name'], item['value']),
                    'type':'pmetric',
                    'behavior': 'number',
                    'color': "#888888",
                    'elapsed': 20.0
                }

                if(sender_config['type'] == "FlashlexSender"):
                    sender = FlashlexMessageSender(sender_config, cache)
                    sender.send(messageModel)




def handleRaceTable(table):
    tree = html.fromstring(etree.tostring(table, pretty_print=True).decode("utf-8"))
    pval = tree.xpath('//p[@style="font-size: 55pt; margin-bottom:-10px"]/text()')
    ival = tree.xpath('//img[@width="100"]/@src')

    items = []
    for i in range(len(ival)):
        name = ival[i].replace("/","").replace(".png","")
        percent = round(float(pval[i].replace("%",""))/100.0, 4)
        if(percent>0.1):
            items.append({'name':name,'value':percent})
    
    return items