---
title: 'The 3D Slicer RVXLiverSegmentation plug-in for interactive liver anatomy reconstruction from medical images'
tags:
  - 3D Slicer
  - medical imaging
  - image segmentation
  - image processing
  - annotation
  - liver
authors:
  - name: Jonas Lamy^[co-first author] 
    affiliation: 1 
  - name: Thibault Pelletier^[co-first author] 
    affiliation: 2
  - name: Guillaume Lienemann^[co-first author]
    affiliation: 3
  - name: Benoît Magnin
    affiliation: 3
  - name: Bertrand Kerautret
    affiliation: 1
  - name: Nicolas Passat
    affiliation: 4
  - name: Julien Finet
    affiliation: 2
  - name: Antoine Vacavant^[corresponding author]
    affiliation: 3
affiliations:
 - name: Université Lyon 2, LIRIS (UMR 5205) Lyon, France
   index: 1
 - name: Kitware SAS, Villeurbanne, France
   index: 2
 - name: Université Clermont Auvergne, CNRS, SIGMA Clermont, Institut Pascal, F-63000, Clermont-Ferrand, France
   index: 3
 - name: Université de Reims Champagne Ardenne, CReSTIC, EA 3804, 51097 Reims, France
   index: 4
date: 01 October 2021
bibliography: paper.bib

---

# Global description 

Annotation plays a key role in the creation of reference datasets that are useful to evaluate medical image processing algorithms and to train machine learning based architectures. `RVXLiverSegmentation` is a 3D Slicer [@3DSlicer2020-Web;@Kikinis2014-3DSlicer] plug-in aimed at speeding-up the annotation of liver anatomy from medical images (CT scans or MRI for intance). This organ has a complex and particular geometry; within its parenchymal volume, the liver receives blood from the portal vein and hepatic artery (the former one being the most visible in medical images), and delivers filtered blood through the hepatic veins, toward inferior vena cava. The blood vessels subdivide into the liver as fine vascular tree structures, which make the segmentation difficult, mostly in MRI modality. To facilitate this task, our plug-in is decomposed into 7 main tabs:

* loading and managing medical imaging data;
* liver segmentation;
* portal veins annotation and segmentation;
* edit portal veins segmentation;
* inferior vena cava annotation and segmentation;
* edit inferior vena cava segmentation;
* tumor segmentation. 


Once the medical image data is loaded into the 3D Slicer interface, the liver can be segmented with the associated tab, either by using interactive tools (such as region growing approaches) or by an automatic deep learning based algorithm (for CT scans only). 
Then, the reconstructions of hepatic vessels (portal vein and inferior vena cava) are based on tree structures interactively constructed by the user, who places the nodes of important branches and bifurcations (with specific anatomical nomenclature) into the scene of the medical image to be processed. After this step, a VMTK (Vascular Modeling Tool Kit) [@a2008-VMTK] module segments the vessels by using those graphs as initialization patterns. The last tab allows the user to segment interactively possible tumoral tissues with dedicated tools.  
This last tab also permits to export the complete scene, comprising:

* segmentation label maps (liver, inferior vena cava, portal vein, tumors);
* portal vein and inferior vena cava intersection positions (fiducial CSV and adjacent matrix);
* the complete scene as a MRB file. 

![Liver segmentation tab.\label{fig:liver_lab}](liver_tab.png)
![Tab for portal vein annotation and segmentation.\label{fig:portal_vein_tab}](portal_vein_tab.png)

# Preliminary results obtained with the plug-in



# Future works

# Acknowledgements

This work was funded by the French \emph{Agence Nationale de la Recherche} (grant ANR-18-CE45-0018, project R-Vessel-X, http://tgi.ip.uca.fr/r-vessel-x). 

# References