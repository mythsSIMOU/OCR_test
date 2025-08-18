# report_generator.py

import json
import csv
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Importation de toutes les classes de détection nécessaires
from column_detector import TwoColumnsPageDetectorDensity  # On utilise l'analyseur de haut niveau pour les colonnes
from row_detector import ThreeColumnsMajorityDetector
from nested_detector import NestedLayoutsDetector
from table_detector import TableDetector

class ReportGenerator:
    """
    Analyse les documents avec plusieurs détecteurs et génère un rapport CSV consolidé.
    """
    def __init__(self, base_dir: str = "result_json", output_file: str = "report_tables.csv"):
        self.base_dir = Path(base_dir)
        self.output_file = Path(output_file)
        
        # Init all detectors
        self.table_detector = TableDetector()
        
        # Liste pour stocker tous les résultats
        self.all_detections = []

    def run_full_analysis(self):
        """
        Parcourt tous les fichiers JSON et exécute les trois types de détection.
        """
        if not self.base_dir.exists():
            print(f"Erreur : Le dossier de base '{self.base_dir}' est introuvable.")
            return

        print("Début de l'analyse complète des documents...")
        
        # rglob("*.json") parcourt tous les sous-dossiers
        for json_file in sorted(self.base_dir.rglob("*.json")):
            # print(f"Analyse du fichier : {json_file.name}")
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for page_data in data:
                page_number = page_data['index']
                document_name = json_file.name
                
                case_label_detector =  self.table_detector.detect_table_label(page_data)
                
                if (case_label_detector):
                    if (case_label_detector['full_page']):
                        self.all_detections.append({
                            'document_name': document_name,
                            'full_page': True,
                            'page_number': page_number,
                            'detection_type': 'detection label',
                            'table_boxes': []
                        })
                    else:
                        self.all_detections.append({
                            'document_name': document_name,
                            'full_page': False,
                            'page_number': page_number,
                            'detection_type': 'detection label',
                            'table_boxes': case_label_detector['list']
                        })
                else:
                    case_3_columns_detector = self.table_detector.detect_3_columns_case(page_data)
                    if (case_3_columns_detector):
                        self.all_detections.append({
                            'document_name': document_name,
                            'full_page': True,
                            'page_number': page_number,
                            'detection_type': '3 columns',
                            'table_boxes': []
                        })
                                
                    

    def save_report(self):
        """
        Sauvegarde la liste des détections dans un fichier CSV.
        """
        if not self.all_detections:
            print("Aucune mise en page complexe détectée. Le rapport est vide.")
            return

        print(f"Sauvegarde du rapport dans '{self.output_file}'...")
        
        # Noms des colonnes pour le fichier CSV
        fieldnames = ['document_name', 'page_number', 'full_page', 'detection_type', 'table_boxes']
        
        with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()  # Écrit la ligne d'en-tête
            writer.writerows(self.all_detections) # Écrit toutes les données

        print(f"Rapport généré avec succès avec {len(self.all_detections)} détections.")


if __name__ == "__main__":
    # Créer et lancer le générateur de rapport
    report_generator = ReportGenerator()
    report_generator.run_full_analysis()
    report_generator.save_report()