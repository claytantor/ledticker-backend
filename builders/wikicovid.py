import requests
import re

from lxml import etree, html

from senders import FlashlexMessageSender

def covid_us_summary(builder_config, sender_config, cache, tz):
    page = requests.get(builder_config['data_url'])
    tree = html.fromstring(page.content)

    tables = tree.xpath('//table[@class="infobox"]')
    for table in tables:
        metrics = handleInfoTable(table)
        sendMetrics(metrics, sender_config, sender_config)

def handleInfoTable(table):
    tree = html.fromstring(etree.tostring(table, pretty_print=True).decode("utf-8"))
    rows = tree.xpath('//tr')
    metrics = []
    for row in rows:
        handleInfoRow(row, metrics)
    return metrics

def handleInfoRow(row, metrics):
    tree = html.fromstring(etree.tostring(row, pretty_print=True).decode("utf-8"))

    header_element = tree.xpath('//th[@scope="row"]/div')

    if(len(header_element)>0 and header_element[0].text=='Deaths'):

        numbers = tree.xpath('//td/div[@class="plainlist"]/ul/li/text()')
        numbers_crawled = []
        for number_text in numbers:
            # print(number_text)
            number_clean = re.findall(r'\d', number_text) 
            if(len(number_clean)>0):
                numbers_crawled.append(int(''.join(number_clean)))

        metrics.append({'name':'US Deaths COVID19', 'value':numbers_crawled[0], 'color':'#f542e0'})

        
def sendMetrics(metrics, sender_config, cache):
    for metric in metrics:
        # print("metric", metric)
        messageModel = {
                'body':'{0}|{1}'.format(
                    metric['name'], metric['value']),
                'type':'metric',
                'behavior': 'number',
                'color': metric['color'],
                "font": "sm-1", 
                'elapsed': 20.0
        }

        if(sender_config['type'] == "FlashlexSender"):
            sender = FlashlexMessageSender(sender_config, cache)
            sender.send(messageModel)
