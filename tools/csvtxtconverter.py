import csv
import re
import argparse
from pathlib import Path

LATITUDES_TXT_NAME = "latitudes.txt"
LONGITUDES_TXT_NAME = "longitudes.txt"

# 2nd number is latitude
# 1st number is longitude

def convertCsvToTxt(csvFilePath, outputFolderPath, outputFolderName=None):
    csvFile = Path(csvFilePath)
    outputFolder = Path(outputFolderPath)

    if not csvFile.is_file():
        print("The file " + csvFilePath + " does not exist")
        return
    
    if not outputFolder.is_dir():
        print("The folder " + outputFolderPath + " does not exist")
        return
    
    subFolderName = csvFile.stem
    if outputFolderName != None:
        subFolderName = outputFolderName
    subFolder = outputFolder / subFolderName
    subFolder.mkdir(parents=True, exist_ok=True)

    with open(csvFilePath, mode="r", newline="", encoding="utf-8") as file:  
        reader = csv.reader(file)

        latitudes = []
        longitudes = []
        for row in reader:
            # Regex expression to extract the coordinates from the csv file
            numbers = re.findall(r"[-+]?\d*\.\d+|\d+", row[0])
            if len(numbers) > 0:
                longitude = numbers[0]
                latitude = numbers[1]
                latitudes.append(latitude)
                longitudes.append(longitude)

        latitudeFile = subFolder / LATITUDES_TXT_NAME
        longitudeFile = subFolder / LONGITUDES_TXT_NAME

        with open(latitudeFile, mode="w", encoding="utf-8") as output:
            for latitude in latitudes:
                output.write(str(latitude) + "\n")

        with open(longitudeFile, mode="w", encoding="utf-8") as output:
            for longitude in longitudes:
                output.write(str(longitude) + "\n")

def convertTxtToCsv(inputFolderPath, outputFolderPath, csvFileName=None):
    inputFolder = Path(inputFolderPath)
    outputFolder = Path(outputFolderPath)

    if not inputFolder.is_dir():
        print("The file " + inputFolder + " does not exist")
        return
    
    if not outputFolder.is_dir():
        print("The folder " + outputFolderPath + " does not exist")
        return
    
    if csvFileName == None:
        csvFileName = inputFolder.stem
    
    latitudes = []
    longitudes = []
    
    with open(inputFolder / LATITUDES_TXT_NAME, "r") as latitudesIn, open(inputFolder / LONGITUDES_TXT_NAME, "r", encoding="utf-8") as longitudesIn:
        for line in latitudesIn:
            stripped = line.strip()
            if stripped != "":
                latitudes.append(stripped)

        for line in longitudesIn:
            stripped = line.strip()
            if stripped != "":
                longitudes.append(stripped)


    if len(latitudes) != len(longitudes):
        print("Latitude and longitude files do not have the same number of lines!")
        return
    
    with open(outputFolder / (csvFileName + ".csv"), "w", newline="", encoding="utf-8") as csvOut:
        writer = csv.writer(csvOut, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["WKT", "name", "description"])

        for i in range(len(latitudes)):
            latitude = latitudes[i]
            longitude = longitudes[i]

            wkt = f'POINT ({longitude} {latitude})'
            name = f"Point {i+1}"
            writer.writerow([wkt, name, ""])



def main():
    parser = argparse.ArgumentParser(
        description="Convert between CSV (with WKT) and separate latitude/longitude TXT files."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    totxt_parser = subparsers.add_parser("totxt", help="Convert CSV file to latitude/longitude TXT files.")
    totxt_parser.add_argument("csv_file", help="Input CSV file to convert.")
    totxt_parser.add_argument("output_dir", help="Directory to save the TXT files.")
    totxt_parser.add_argument(
        "--name",
        "-n",
        help="Name of the folder that is created",
        default=None
    )

    tocsv_parser = subparsers.add_parser("tocsv", help="Convert latitude/longitude TXT files to CSV.")
    tocsv_parser.add_argument("input_dir", help="Folder that contains latitudes.txt and longitudes.txt")
    tocsv_parser.add_argument("output_dir", help="Directory to save the CSV file.")
    tocsv_parser.add_argument(
        "--name",
        "-n",
        help="Name of the folder that is created",
        default=None
    )

    args = parser.parse_args()

    if args.command == "totxt":
        convertCsvToTxt(args.csv_file, args.output_dir, args.name)
    elif args.command == "tocsv":
        convertTxtToCsv(args.input_dir, args.output_dir, args.name)

main()