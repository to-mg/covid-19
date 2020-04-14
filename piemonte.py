#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
get COVID data from
https://www.regione.piemonte.it/web/covid-19-mappa-dei-contagi-piemonte
get ISTAT codici comuni from
https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv
create a csv file with the merged data

csv file name has following format
dati_YYYY_MM_DD_da_regione_piemonte.csv

csv file has following columns
"Comune", "Codice ISTAT", "Abitanti", "Positivi", "Rapporto", "Data"
not available data have the value -1
"""
import csv
from datetime import datetime
import os
import sys
import time
import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/39.0.2171.95 Safari/537.36")
REQUEST_HEADERS = {'User-Agent': UA}


def load_comuni():
    """
    load code and name for each comune from istat provided csv file
    create a dictionary mapping code to name
    """
    url_istat = "https://www.istat.it/storage/codici-unita-amministrative/" + \
                "Elenco-comuni-italiani.csv"
    ifile = 'Elenco-comuni-italiani.csv'
    if not os.path.isfile(ifile):
        print("Downloading ", ifile, " from ISTAT")
        buf = requests.get(url_istat, headers=REQUEST_HEADERS).text
        open(ifile, 'wt', encoding='ISO-8859-1').write(buf)
    comuni = {}
    with open(ifile, 'rt', encoding='ISO-8859-1') as fin:
        reader = csv.reader(fin, delimiter=";")
        for row in reader:
            if row[0].find('Codice') >= 0:
                # skip header row
                continue
            elif row[0] != '01':
                # done with Piemonte
                break
            else:
                comuni[row[4]] = row[5]
    return comuni


def main():
    """
    get the dictionary code/name for all the comuni
    navigate to the page with the map
    move to frame with the map
    get the variable with the data
    write the data csv format to a file
    """
    comuni = load_comuni()
    url = "https://www.regione.piemonte.it/web/" + \
          "covid-19-mappa-dei-contagi-piemonte"
    # run the selected browser
    # if required, add specific options to options dictionary
    options = {}
    # comment / uncomment following two lines to select selenium driver
    # driver = webdriver.Firefox(chrome_options=options)
    driver = webdriver.Chrome(chrome_options=options)
    driver.implicitly_wait(10)
    # navigate
    try:
        driver.get(url)
    except TimeoutException:
        print("Timeout in loading ", url, " retry later")
        sys.exit()
    time.sleep(3)
    # move to map frame
    iframe = driver.find_elements_by_tag_name('iframe')
    if not iframe:
        print("Iframe not found, the page may have changed")
        sys.exit()
    driver.switch_to.frame(iframe[0])
    # get the keys (ISTAT codes) in javascript object classificationData
    keys = driver.execute_script("return Object.keys(classificationData)")
    if not keys:
        print("Javascript object classificationData not found in the frame")
        print("The page may have changed")
        sys.exit()
    # js code for getting the data associated to each ISTAT code
    get_value_function = "return classificationData[arguments[0]];"
    # create csv writer
    today = datetime.strftime(datetime.now(), "%Y_%m_%d")
    ofile = "dati_" + today + "_da_regione_piemonte.csv"
    with open(ofile, 'wt') as fout:
        writer = csv.writer(fout, delimiter=";")
        # write file header
        row = ["Comune", "Codice ISTAT", "Abitanti",
               "Positivi", "Rapporto", "Data"]
        writer.writerow(row)
        # deal with each ISTAT code
        # -1 means missing data
        for key in keys:
            # get the data related to the ISTAT code
            item = driver.execute_script(get_value_function, key)
            try:
                item['nome'] = comuni[item['comune_ist']]
            except KeyError:
                item['nome'] = "Sconosciuto"
                print("ISTAT code %s not found" % key)
            print(item['nome'])
            row[0] = item['nome']
            row[1] = item['comune_ist']
            try:
                row[2] = item['pop_tot']
            except KeyError:
                row[2] = -1
            # write the data for each reported day
            if "RAPPORTO" in item:
                data = zip(item["POSITIVI"], item["RAPPORTO"])
                for positives, ratio in data:
                    row[3] = positives['value']
                    row[4] = ratio['value']
                    day = positives['giorno'][:2]
                    month = positives['giorno'][2:]
                    row[5] = "2020/" + month + "/" + day
            else:
                for positives in item["POSITIVI"]:
                    row[3] = positives['value']
                    row[4] = -1
                    day = positives['giorno'][:2]
                    month = positives['giorno'][2:]
                    row[5] = "2020/" + month + "/" + day
            writer.writerow(row)

    driver.close()
    driver.quit()


if __name__ == "__main__":
    main()
