import streamlit as st

# importing necessary modules
import networkx as nx
from gnpsdata import taskresult
import os
import csv
import pandas as pd
import pandas as pd
import numpy as np
import os
import itertools
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
from plotly.subplots import make_subplots
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.preprocessing import StandardScaler
from scipy.spatial import distance
from sklearn.decomposition import PCA
import scipy.stats as stats
import pingouin as pg
import skbio
from ipyfilechooser import FileChooser
from ipywidgets import interact
from pynmranalysis.normalization import PQN_normalization
import warnings

from qiime2 import Visualization

from gnpsdata import workflow_fbmn

# Write the page label
st.set_page_config(
    page_title="Homepage",
    page_icon="👋",
)

# Organization
data_root = "/app/data/"

# GNPS/GNPS2 task id
task = st.text_input("Enter GNPS/GNPS2 Task ID", "cf6e14abf5604f47b28b467a513d3532")
gnps_server = st.selectbox("GNPS Server", ["gnps1", "gnps2"], index=0)

if gnps_server == "gnps1":    
    # Download quantification
    workflow_fbmn.download_quantification(task, f"{data_root}/quant.csv", gnps2=False)

    # Downloading metadata
    workflow_fbmn.download_metadata(task, os.path.join(data_root, f"{data_root}/unprocessed_metadata.tsv"), gnps2=False)

    # Downloading the qiime artifact
    workflow_fbmn.download_qiime2(task, os.path.join(data_root, f"{data_root}/qiime_table.qza"))

elif gnps_server == "gnps2":
    st.stop("NOT IMPLEMENTED")
  
#read metadata file
metadata_df = pd.read_csv(f"{data_root}/unprocessed_metadata.tsv", sep = "\t", index_col=False)
#rename 1st column to "#sample id
metadata_df = metadata_df.rename(columns={"filename":"sample id"})
#convert back to .tsv
metadata_df.to_csv(f"{data_root}/metadata.tsv", sep="\t", index=False)

st.write("Metadata Reformatted")
st.write(metadata_df)

# Blank Removal
blank_removal = st.checkbox("Blank Removal", value=True)

if blank_removal:
    # Doing this via Qiime Plugin
    cmd = """qiime blankremoval-plugin blankremoval-function \
    --i-input-artifact {} \
    --p-metadatafile {} \
    --o-output-artifact {}""".format(os.path.join(data_root, "qiime_table.qza"),
                                                    os.path.join(data_root, "unprocessed_metadata.tsv"),
                                                    os.path.join(data_root, "qiime_table_blanksremoved.qza"))

    st.code(cmd, language='bash')

    ret = os.system(cmd)
    if ret != 0:
        st.stop("Error in Blank Removal")

    blank_remove_artifact = f'{data_root}/qiime_table_blanksremoved.qza'

    st.write("Blanks Removed")
else:
    # Using Default
    blank_remove_artifact = f'{data_root}/qiime_table.qza'


# Imputation
cmd = f"""qiime imputation-plugin imputation-function \
--i-input-artifact '{blank_remove_artifact}' \
--o-output-artifact '{data_root}/qiime_table_blanksremoved_imputed.qza'"""

st.code(cmd, language='bash')

ret = os.system(cmd)
if ret != 0:
    st.write("Error in Imputation, bypassing")
    # Skipping so using input
    imputed_artifact = blank_remove_artifact
else:
    st.write("Data Imputed")
    imputed_artifact = f'{data_root}/qiime_table_blanksremoved_imputed.qza'

# Normalization
cmd = f"""qiime normalization-plugin normalize-function \
--i-input-artifact '{imputed_artifact}' \
--o-output-artifact-frequency '{data_root}/qiime_table_blanksremoved_imputed_normalization.qza' \
--o-output-artifact-relative '{data_root}/qiime_table_blanksremoved_imputed_normalization_relative.qza'"""

st.code(cmd, language='bash')

ret = os.system(cmd)
if ret != 0:
    st.stop("Error in Normalization")

st.write("Normalized")

# Distance Matrix
p_metric = st.selectbox("Select Metric", ["canberra_adkins", "braycurtis", "jaccard", "euclidean"], index=0)

cmd = f"""qiime diversity beta \
  --i-table '{data_root}/qiime_table_blanksremoved_imputed_normalization.qza' \
  --p-metric {p_metric} \
  --o-distance-matrix '{data_root}/distance_matrix.qza'"""

st.code(cmd, language='bash')

ret = os.system(cmd)
if ret != 0:
    st.stop("Error in Distance Matrix")

# PCoA
cmd = f"""qiime diversity pcoa \
    --i-distance-matrix '{data_root}/distance_matrix.qza' \
    --o-pcoa '{data_root}/pcoa.qza'"""

st.code(cmd, language='bash')

ret = os.system(cmd)
if ret != 0:
    st.stop("Error in PCoA")

# PCoA Plot

cmd = f"""qiime emperor plot \
    --i-pcoa '{data_root}/pcoa.qza' \
    --m-metadata-file '{data_root}/metadata.tsv' \
    --o-visualization '{data_root}/pcoa.qzv'"""

st.code(cmd, language='bash')

ret = os.system(cmd)
if ret != 0:
    st.stop("Error in PCoA Plot")

st.write("PCoA Emperor")

with open(f'{data_root}/pcoa.qzv', 'rb') as f:
   st.download_button('Download pcoa.qzv', f, file_name='pcoa.qzv')




# Loading Visualization into Dashboard

# TODO to extract and visualize
metadata_columns = list(metadata_df.columns)

# Permanova
metadata_column_permanova = st.selectbox("Select Metadata Column for Permanova", metadata_columns, placeholder="Choose an option")

permanova_cmd = f"""qiime diversity beta-group-significance \
  --i-distance-matrix '{data_root}/distance_matrix.qza' \
  --m-metadata-file '{data_root}/metadata.tsv' \
  --m-metadata-column '{metadata_column_permanova}' \
  --o-visualization '{data_root}/permanova.qzv'"""

st.code(permanova_cmd, language='bash')

ret = os.system(permanova_cmd)
if ret != 0:
    st.stop("Error in Permanova")

st.write("Permanova")


# # Classified Data/Heatmap
# metadata_column = 'ATTRIBUTE_Sample_Area'
# estimator = 'RandomForestClassifier'
# n_estimators = 500
# random_state = 123

# cmd =  """qiime sample-classifier classify-samples \
#   --i-table ./QIIME2/output_QIIME2_Notebook/qiime_table.qza \
#   --m-metadata-file ./QIIME2/output_QIIME2_Notebook/metadata.tsv \
#   --m-metadata-column $metadata_column \
#   --p-optimize-feature-selection \
#   --p-parameter-tuning \
#   --p-estimator $estimator \
#   --p-n-estimators $n_estimators \
#   --p-random-state $random_state \
#   --o-accuracy-results ./QIIME2/output_QIIME2_Notebook/accuracy_results.qzv \
#   --o-feature-importance ./QIIME2/output_QIIME2_Notebook/feature_importance.qza \
#   --o-heatmap ./QIIME2/output_QIIME2_Notebook/heatmap.qzv \
#   --o-model-summary ./QIIME2/output_QIIME2_Notebook/model_summary.qzv \
#   --o-predictions ./QIIME2/output_QIIME2_Notebook/predictions.qza \
#   --o-probabilities ./QIIME2/output_QIIME2_Notebook/probabilities.qza \
#   --o-sample-estimator ./QIIME2/output_QIIME2_Notebook/sample_estimator.qza \
#   --o-test-targets ./QIIME2/output_QIIME2_Notebook/test_targets.qza \
#   --o-training-targets ./QIIME2/output_QIIME2_Notebook/training_targets.qza"""

# ret = os.system(cmd)
# if ret != 0:
#     st.stop("Error in Classified Data")

