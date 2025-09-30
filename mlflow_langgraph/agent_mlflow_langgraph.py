import os
import mlflow
import numpy as np
import requests
import json
from typing_extensions import TypedDict
from typing import Dict, List, Optional
from langgraph.graph import StateGraph, START, END
from dataclasses import dataclass
import webbrowser
import tempfile

# ┌─ AlphaFold API Integration ─────────────────────────────────────────────────
def analyze_protein_sequence(sequence: str) -> Dict:
    """Analyze protein sequence for folding characteristics (ColabFold-inspired)"""
    if not sequence:
        return {'length': 0, 'disorder_regions': [], 'druggability_score': 0.5}
    
    # Simple disorder prediction
    disorder_regions = []
    window_size = 10
    for i in range(0, len(sequence) - window_size, 5):
        window = sequence[i:i+window_size]
        disorder_aa = 'PQSTNKRH'  # Disorder-promoting amino acids
        disorder_score = sum(1 for aa in window if aa in disorder_aa) / len(window)
        if disorder_score > 0.6:
            disorder_regions.append((i, i+window_size))
    
    # Druggability assessment
    hydrophobic_aa = 'AILMFWYV'
    charged_aa = 'DEKR'
    hydrophobic_ratio = sum(1 for aa in sequence if aa in hydrophobic_aa) / len(sequence)
    charged_ratio = sum(1 for aa in sequence if aa in charged_aa) / len(sequence)
    druggability_score = min(1.0, (hydrophobic_ratio * 2 + charged_ratio) * 0.8)
    
    return {
        'length': len(sequence),
        'disorder_regions': disorder_regions,
        'druggability_score': druggability_score
    }

def query_alphafold_server(sequences: List[str], job_name: str = "drug_discovery") -> Dict:
    """Query AlphaFold Server for protein complex prediction"""
    # AlphaFold Server integration for protein-protein interactions
    # Note: This would require API authentication in production
    
    try:
        # Simulate AlphaFold Server response for p53-MDM2 interaction
        if len(sequences) > 1:
            # Multi-chain complex prediction
            return {
                'job_id': f'af_server_{job_name}',
                'status': 'completed',
                'confidence_scores': [0.85, 0.78],  # Per chain
                'interface_confidence': 0.82,
                'binding_sites': [
                    {'chain': 'A', 'residues': [175, 248, 273], 'confidence': 0.85},
                    {'chain': 'B', 'residues': [25, 32, 54], 'confidence': 0.78}
                ],
                'pdb_content': None  # Would contain actual PDB data
            }
        else:
            # Single chain prediction
            return {
                'job_id': f'af_server_{job_name}',
                'status': 'completed', 
                'confidence_scores': [0.85],
                'binding_sites': [{'chain': 'A', 'residues': [175, 248, 273], 'confidence': 0.85}],
                'pdb_content': None
            }
            
    except Exception as e:
        print(f"AlphaFold Server error: {e}")
        return {
            'job_id': 'fallback',
            'status': 'failed',
            'confidence_scores': [0.75],
            'binding_sites': [{'chain': 'A', 'residues': [175, 248, 273], 'confidence': 0.75}]
        }

def fetch_alphafold_data(uniprot_id: str) -> Dict:
    """Fetch protein data from AlphaFold API with sequence analysis"""
    base_url = "https://alphafold.ebi.ac.uk/api"
    
    try:
        # Get prediction data
        pred_response = requests.get(f"{base_url}/prediction/{uniprot_id}", timeout=10)
        if pred_response.status_code != 200:
            raise Exception(f"Prediction API failed: {pred_response.status_code}")
        
        pred_data = pred_response.json()
        
        # Get UniProt summary
        summary_response = requests.get(f"{base_url}/uniprot/summary/{uniprot_id}.json", timeout=10)
        summary_data = summary_response.json() if summary_response.status_code == 200 else {}
        
        # Calculate average confidence from prediction data
        confidence = 0.85  # Default
        if pred_data and len(pred_data) > 0:
            entry = pred_data[0]
            if 'confidenceScore' in entry:
                confidence = entry['confidenceScore'] / 100.0
        
        # p53 sequence for analysis
        p53_sequence = "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGPDEAPRMPEAAPPVAPAPAAPTPAAPAPAPSWPLSSSVPSQKTYQGSYGFRLGFLHSGTAKSVTCTYSPALNKMFCQLAKTCPVQLWVDSTPPPGTRVRAMAIYKQSQHMTEVVRRCPHHERCSDSDGLAPPQHLIRVEGNLRVEYLDDRNTFRHSVVVPYEPPEVGSDCTTIHYNYMCNSSCMGGMNRRPILTIITLEDSSGNLLGRNSFEVRVCACPGRDRRTEEENLRKKGEPHHELPPGSTKRALPNNTSSSPQPKKKPLDGEYFTLQIRGRERFEMFRELNEALELKDAQAGKEPGGSRAHSSHLKSKKGQSTSRHKKLMFKTEGPDSD"
        sequence_analysis = analyze_protein_sequence(p53_sequence)
        
        # Query AlphaFold Server for enhanced structure prediction
        mdm2_sequence = "MCNTNMSVPTDGAVTTSQIPASEQETLVRPKPLLLKLLKSVGAQKDTYTMKEVLFYLGQYIMTKRLYDEKQQHIVYCSNDLLGDLFGVPSFSVKEHRKIYTMIYRNLVVVNQQESSDSGTSVSEN"
        af_server_result = query_alphafold_server([p53_sequence, mdm2_sequence], f"p53_mdm2_{uniprot_id}")
        
        return {
            'uniprot_id': uniprot_id,
            'name': summary_data.get('uniprotDescription', f'Protein {uniprot_id}'),
            'confidence': confidence,
            'pdb_url': pred_data[0].get('pdbUrl', '') if pred_data else '',
            'cif_url': pred_data[0].get('cifUrl', '') if pred_data else '',
            'sequence_analysis': sequence_analysis,
            'alphafold_server': af_server_result
        }
        
    except Exception as e:
        print(f"AlphaFold API error for {uniprot_id}: {e}")
        return {
            'uniprot_id': uniprot_id,
            'name': f'Protein {uniprot_id}',
            'confidence': 0.75,  # Fallback
            'pdb_url': '',
            'cif_url': '',
            'sequence_analysis': {'length': 393, 'disorder_regions': [], 'druggability_score': 0.65},
            'alphafold_server': {'status': 'failed', 'confidence_scores': [0.75]}
        }

# ┌─ MLflow Declaration & Setup ───────────────────────────────────────────────
# MLflow setup will be done in main function to avoid connection issues
# └──────────────────────────────────────────────────────────────────────────────

@dataclass
class ProteinTarget:
    uniprot_id: str
    name: str
    alphafold_confidence: float
    binding_sites: List[Dict]

@dataclass
class Compound:
    chembl_id: str
    smiles: str
    molecular_weight: float
    binding_affinity: float
    admet_score: float

class RareDiseaseState(TypedDict):
    # Disease Context
    disease_name: str
    target_protein: ProteinTarget
    patient_genotype: Dict[str, str]
    
    # Virtual Patient Cohort
    cohort_size: int
    age_range: tuple
    genetic_variants: List[str]
    
    # Drug Candidates
    compounds: List[Compound]
    lead_compound: Optional[Compound]
    
    # Trial Simulation Results
    efficacy_score: float
    safety_score: float
    trial_success_probability: float
    recommended_for_trial: bool

def build_drug_discovery_agent(efficacy_threshold: float = 0.7):
    """
    Drug Discovery Pipeline:
      • FetchProteinData    - Get AlphaFold structure
      • ScreenCompounds     - Query ChEMBL for candidates
      • SimulateTrial       - Run virtual clinical trial
      • EvaluateCandidate   - Assess trial readiness
    """
    def fetch_protein_data(state: RareDiseaseState) -> RareDiseaseState:
        # Fetch real AlphaFold data
        uniprot_id = "P04637"  # p53 tumor suppressor
        alphafold_data = fetch_alphafold_data(uniprot_id)
        
        # Enhanced binding site prediction using sequence analysis and AlphaFold Server
        seq_analysis = alphafold_data.get('sequence_analysis', {})
        af_server = alphafold_data.get('alphafold_server', {})
        
        druggability_score = seq_analysis.get('druggability_score', 0.65)
        
        # Use AlphaFold Server binding sites if available
        binding_sites = af_server.get('binding_sites', [{'chain': 'A', 'residues': [175, 248, 273], 'confidence': 0.72}])
        enhanced_sites = []
        for site in binding_sites:
            enhanced_sites.append({
                'residues': site['residues'],
                'druggability': druggability_score * site.get('confidence', 0.75),
                'chain': site.get('chain', 'A')
            })
        
        target = ProteinTarget(
            uniprot_id=alphafold_data['uniprot_id'],
            name=alphafold_data['name'],
            alphafold_confidence=alphafold_data['confidence'],
            binding_sites=enhanced_sites
        )
        state['target_protein'] = target
        return state

    def screen_compounds(state: RareDiseaseState) -> RareDiseaseState:
        # Simulate ChEMBL compound screening
        compounds = [
            Compound("CHEMBL123", "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", 206.28, 8.5, 0.68),
            Compound("CHEMBL456", "CC1=CC=C(C=C1)C(=O)NC2=CC=CC=C2", 211.26, 7.8, 0.74),
            Compound("CHEMBL789", "COC1=CC=C(C=C1)C=CC(=O)O", 178.19, 6.9, 0.81)
        ]
        state['compounds'] = compounds
        state['lead_compound'] = max(compounds, key=lambda c: c.binding_affinity * c.admet_score)
        return state

    def simulate_trial(state: RareDiseaseState) -> RareDiseaseState:
        # Virtual clinical trial simulation
        lead = state['lead_compound']
        if lead is None:
            state['efficacy_score'] = 0.0
            state['safety_score'] = 0.0
            state['trial_success_probability'] = 0.0
            return state
        
        # Efficacy based on binding affinity and target confidence
        efficacy = (lead.binding_affinity / 10.0) * state['target_protein'].alphafold_confidence
        
        # Safety based on ADMET properties
        safety = lead.admet_score * 0.9  # Conservative safety margin
        
        # Success probability combines efficacy, safety, and genetic factors
        genetic_modifier = 1.0 + (0.1 * len(state['genetic_variants']))
        success_prob = (efficacy * 0.6 + safety * 0.4) * genetic_modifier
        
        state['efficacy_score'] = min(efficacy, 1.0)
        state['safety_score'] = min(safety, 1.0)
        state['trial_success_probability'] = min(success_prob, 1.0)
        return state

    def evaluate_candidate(state: RareDiseaseState) -> RareDiseaseState:
        state['recommended_for_trial'] = state['trial_success_probability'] >= efficacy_threshold
        return state

    graph = StateGraph(RareDiseaseState)
    graph.add_node("FetchProteinData", fetch_protein_data)
    graph.add_node("ScreenCompounds", screen_compounds)
    graph.add_node("SimulateTrial", simulate_trial)
    graph.add_node("EvaluateCandidate", evaluate_candidate)
    graph.add_edge(START, "FetchProteinData")
    graph.add_edge("FetchProteinData", "ScreenCompounds")
    graph.add_edge("ScreenCompounds", "SimulateTrial")
    graph.add_edge("SimulateTrial", "EvaluateCandidate")
    graph.add_edge("EvaluateCandidate", END)
    
    return graph.compile()

def create_rare_disease_scenario() -> dict:
    """Generate rare disease drug discovery scenario"""
    return {
        'disease_name': 'Li-Fraumeni Syndrome',
        'cohort_size': 500,
        'age_range': (25, 65),
        'genetic_variants': ['TP53_R175H', 'TP53_R248W', 'TP53_R273H'],
        'patient_genotype': {'TP53': 'R175H/WT', 'MDM2': 'SNP309_T/G'},
        'compounds': [],
        'lead_compound': None,
        'efficacy_score': 0.0,
        'safety_score': 0.0,
        'trial_success_probability': 0.0,
        'recommended_for_trial': False
    }

def generate_3dmol_visualization(compounds: List[Compound], protein_target: ProteinTarget) -> str:
    """Generate HTML with 3Dmol.js visualization of compounds and protein"""
    
    # Try to get real AlphaFold PDB data
    alphafold_data = fetch_alphafold_data(protein_target.uniprot_id)
    pdb_url = alphafold_data.get('pdb_url', '')
    
    compound_info_html = ""
    for i, compound in enumerate(compounds[:3]):
        compound_info_html += f"""
        <div class="compound-info">
            <h3>{compound.chembl_id}</h3>
            <p><strong>SMILES:</strong> {compound.smiles}</p>
            <p><strong>Binding Affinity:</strong> {compound.binding_affinity:.1f}</p>
            <p><strong>ADMET Score:</strong> {compound.admet_score:.2f}</p>
            <div id="viewer{i}" class="viewer"></div>
        </div>
        """
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Drug Discovery Visualization</title>
    <script src="https://3Dmol.csb.pitt.edu/build/3Dmol-min.js"></script>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background: #f9f9f9; 
            position: relative;
        }}
        .viewer {{ 
            width: 400px; 
            height: 300px; 
            margin: 10px auto; 
            border: 2px solid #333; 
            background: white;
            position: relative;
            display: block;
        }}
        .compound-info {{ 
            margin: 15px auto; 
            padding: 15px; 
            background: white; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            max-width: 450px;
        }}
        .status {{ 
            padding: 10px; 
            background: #e8f4fd; 
            border-left: 4px solid #2196F3; 
            margin: 10px 0; 
        }}
        .error {{ 
            background: #ffebee; 
            border-left-color: #f44336; 
        }}
    </style>
</head>
<body>
    <h1>Drug Discovery Visualization - Li-Fraumeni Syndrome</h1>
    
    <div class="status" id="status">Loading 3Dmol.js library...</div>
    
    <h2>Target Protein: {protein_target.name}</h2>
    <p><strong>UniProt ID:</strong> {protein_target.uniprot_id} | <strong>AlphaFold Confidence:</strong> {protein_target.alphafold_confidence:.2f}</p>
    <div id="protein-viewer" class="viewer"></div>
    
    <h2>Lead Compounds</h2>
    {compound_info_html}
    
    <script>
        function updateStatus(message, isError = false) {{
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = isError ? 'status error' : 'status';
        }}
        
        // Wait for DOM to be fully loaded
        document.addEventListener('DOMContentLoaded', function() {{
            // Check if 3Dmol is loaded
            if (typeof $3Dmol === 'undefined') {{
                updateStatus('3Dmol.js failed to load. Check internet connection.', true);
                return;
            }}
            
            updateStatus('3Dmol.js loaded successfully. Rendering molecules...');
            
            setTimeout(function() {{
                try {{
                    // Protein visualization with AlphaFold data
                    const proteinViewer = $3Dmol.createViewer('protein-viewer');
                    const alphafoldPdbUrl = '{pdb_url}';
                    
                    if (alphafoldPdbUrl && alphafoldPdbUrl.length > 0) {{
                        // Load real AlphaFold structure
                        fetch(alphafoldPdbUrl)
                            .then(response => response.text())
                            .then(pdbData => {{
                                proteinViewer.addModel(pdbData, 'pdb');
                                proteinViewer.setStyle({{}}, {{cartoon: {{colorscheme: 'ssJmol'}}}});
                                proteinViewer.setBackgroundColor('white');
                                proteinViewer.zoomTo();
                                proteinViewer.render();
                                updateStatus('Loaded real AlphaFold structure!');
                            }})
                            .catch(error => {{
                                console.error('Failed to load AlphaFold structure:', error);
                                // Fallback to demo structure
                                loadDemoProtein();
                            }});
                    }} else {{
                        loadDemoProtein();
                    }}
                    
                    function loadDemoProtein() {{
                        const pdbData = `ATOM      1  N   ALA A   1      -8.901   4.127  -0.555  1.00 11.99           N  
ATOM      2  CA  ALA A   1      -8.608   3.135  -1.618  1.00 11.99           C  
ATOM      3  C   ALA A   1      -7.221   2.458  -1.897  1.00 11.99           C  
ATOM      4  O   ALA A   1      -6.632   2.674  -2.955  1.00 11.99           O  
ATOM      5  CB  ALA A   1      -9.062   3.898  -2.849  1.00 11.99           C  
ATOM      6  N   GLY A   2      -6.888   1.618  -0.932  1.00 11.99           N  
ATOM      7  CA  GLY A   2      -5.618   0.849  -0.967  1.00 11.99           C  
ATOM      8  C   GLY A   2      -4.509   1.433  -0.111  1.00 11.99           C  
ATOM      9  O   GLY A   2      -4.277   1.093   1.049  1.00 11.99           O  
END`;
                        proteinViewer.addModel(pdbData, 'pdb');
                        proteinViewer.setStyle({{}}, {{sphere: {{colorscheme: 'Jmol', radius: 0.8}}}});
                        proteinViewer.setBackgroundColor('white');
                        proteinViewer.zoomTo();
                        proteinViewer.render();
                        updateStatus('Loaded demo protein structure');
                    }}
                    
                    // Compound visualizations using SDF format (3Dmol.js compatible)
                    const compoundData = [
                        {{
                            id: 'CHEMBL123',
                            name: 'Ibuprofen-like',
                            sdf: `
  Mrv2014 01010000002D          

 13 13  0  0  0  0            999 V2000
   -1.2990    0.7500    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -2.0135    0.3375    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -2.0135   -0.4875    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -1.2990   -0.9000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -0.5845   -0.4875    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -0.5845    0.3375    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.1300    0.7500    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.8445    0.3375    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.5590    0.7500    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    2.2735    0.3375    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    2.9880    0.7500    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    2.2735   -0.4875    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    0.8445   -0.4875    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  2  0  0  0  0
  2  3  1  0  0  0  0
  3  4  2  0  0  0  0
  4  5  1  0  0  0  0
  5  6  2  0  0  0  0
  6  1  1  0  0  0  0
  6  7  1  0  0  0  0
  7  8  1  0  0  0  0
  8  9  1  0  0  0  0
  9 10  1  0  0  0  0
 10 11  1  0  0  0  0
 10 12  2  0  0  0  0
  8 13  1  0  0  0  0
M  END
$$$$`
                        }},
                        {{
                            id: 'CHEMBL456',
                            name: 'Benzamide derivative',
                            sdf: `
  Mrv2014 01010000002D          

 14 14  0  0  0  0            999 V2000
   -2.1434    0.2063    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -1.4289   -0.2062    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -0.7145    0.2063    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.0000   -0.2062    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.7145    0.2063    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.7145    1.0313    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.0000    1.4438    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -0.7145    1.0313    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -1.4289    1.4438    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -2.1434    1.0313    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.4289   -0.2062    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    2.1434    0.2063    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    1.4289   -1.0312    0.0000 N   0  0  0  0  0  0  0  0  0  0  0  0
   -2.8579   -0.2062    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  2  0  0  0  0
  2  3  1  0  0  0  0
  3  4  2  0  0  0  0
  4  5  1  0  0  0  0
  5  6  2  0  0  0  0
  6  7  1  0  0  0  0
  7  8  2  0  0  0  0
  8  3  1  0  0  0  0
  8  9  1  0  0  0  0
  9 10  2  0  0  0  0
 10  1  1  0  0  0  0
  5 11  1  0  0  0  0
 11 12  2  0  0  0  0
 11 13  1  0  0  0  0
  1 14  1  0  0  0  0
M  END
$$$$`
                        }},
                        {{
                            id: 'CHEMBL789',
                            name: 'Ferulic acid-like',
                            sdf: `
  Mrv2014 01010000002D          

 12 12  0  0  0  0            999 V2000
   -1.7321    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -1.0176   -0.4125    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -0.3031    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.4114   -0.4125    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.1259    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.1259    0.8250    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.4114    1.2375    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -0.3031    0.8250    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.8404   -0.4125    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    2.5549    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    3.2694   -0.4125    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    3.9839    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  2  0  0  0  0
  2  3  1  0  0  0  0
  3  4  2  0  0  0  0
  4  5  1  0  0  0  0
  5  6  2  0  0  0  0
  6  7  1  0  0  0  0
  7  8  2  0  0  0  0
  8  3  1  0  0  0  0
  9 10  1  0  0  0  0
 10 11  2  0  0  0  0
 11 12  1  0  0  0  0
  5  9  1  0  0  0  0
M  END
$$$$`
                        }}
                    ];
                    
                    compoundData.forEach((compound, i) => {{
                        setTimeout(function() {{
                            try {{
                                const viewer = $3Dmol.createViewer(`viewer${{i}}`);
                                viewer.addModel(compound.sdf, 'sdf');
                                viewer.setStyle({{}}, {{stick: {{colorscheme: 'Jmol', radius: 0.2}}}});
                                viewer.addStyle({{}}, {{sphere: {{colorscheme: 'Jmol', radius: 0.3}}}});
                                viewer.setBackgroundColor('white');
                                viewer.zoomTo();
                                viewer.render();
                                console.log(`Rendered ${{compound.id}}`);
                            }} catch (e) {{
                                console.error(`Error rendering ${{compound.id}}:`, e);
                            }}
                        }}, i * 800);
                    }});
                    
                    setTimeout(function() {{
                        updateStatus('Molecular visualization complete!');
                    }}, 4000);
                    
                }} catch (error) {{
                    console.error('Visualization error:', error);
                    updateStatus('Error rendering molecules: ' + error.message, true);
                }}
            }}, 2000); // Wait 2 seconds for 3Dmol to fully initialize
        }});
    </script>
</body>
</html>
    """
    
    return html_content

def main(scenario_data: Optional[dict] = None, threshold: float = 0.65, visualize: bool = True):
    if scenario_data is None:
        scenario_data = create_rare_disease_scenario()
    
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns"))
    mlflow.set_experiment("rare_disease_drug_discovery")
    
    app = build_drug_discovery_agent(efficacy_threshold=threshold)

    with mlflow.start_run(run_name="virtual_clinical_trial") as run:
        mlflow.log_param("efficacy_threshold", threshold)
        mlflow.log_param("disease", scenario_data['disease_name'])
        mlflow.log_param("cohort_size", scenario_data['cohort_size'])
        
        initial_state = RareDiseaseState(**scenario_data)
        final_state = app.invoke(initial_state)
        
        print(f"\nDrug Discovery Results for {final_state['disease_name']}:")
        print(f"  Target: {final_state['target_protein'].name}")
        print(f"  Lead Compound: {final_state['lead_compound'].chembl_id}")
        print(f"  Efficacy Score: {final_state['efficacy_score']:.3f}")
        print(f"  Safety Score: {final_state['safety_score']:.3f}")
        print(f"  Trial Success Probability: {final_state['trial_success_probability']:.3f}")
        print(f"  Recommended for Trial: {final_state['recommended_for_trial']}")

        # Generate and save molecular visualization
        if visualize:
            html_content = generate_3dmol_visualization(final_state['compounds'], final_state['target_protein'])
            viz_path = os.path.join(os.getcwd(), "molecular_visualization.html")
            with open(viz_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Log visualization as MLflow artifact
            mlflow.log_artifact(viz_path, "visualizations")
            print(f"\n3D Molecular visualization saved to: {viz_path}")
            print("Opening visualization in browser...")
            webbrowser.open(f"file://{viz_path}")

        mlflow.log_metric("efficacy_score", final_state['efficacy_score'])
        mlflow.log_metric("safety_score", final_state['safety_score'])
        mlflow.log_metric("trial_success_probability", final_state['trial_success_probability'])
        mlflow.log_metric("trial_ready", int(final_state['recommended_for_trial']))
        
        mlflow.set_tag("agent_type", "drug_discovery")
        mlflow.set_tag("target_protein", final_state['target_protein'].uniprot_id)
        recommendation = "PROCEED" if final_state['recommended_for_trial'] else "HALT"
        mlflow.log_param("trial_recommendation", recommendation)


if __name__ == "__main__":
    main(visualize=True)
