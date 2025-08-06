# Short-Read MNGS Workflow Diagram

```mermaid
flowchart TB
    %% Input
    Input["Input: FASTQ Files<br/>(Single or Paired-end)"]
    
    %% Stage 1: Host Filter
    subgraph Stage1["Stage 1: Host Filter"]
        direction TB
        S1_Validate["Validate Input<br/>(Truncate if needed)"]
        S1_ERCC["ERCC Filter<br/>(Bowtie2)"]
        S1_QC["Quality Control<br/>(fastp: trim, filter)"]
        S1_Kallisto["Kallisto<br/>(Transcript quantification)"]
        S1_Host["Host Filter<br/>(Bowtie2 → HISAT2)"]
        S1_Human["Human Filter<br/>(if non-human host)<br/>(Bowtie2 → HISAT2)"]
        S1_Dedup["Deduplication<br/>(CZID Dedup)"]
        S1_Subsample["Subsample & Convert<br/>(FASTQ → FASTA)"]
        
        S1_Validate --> S1_ERCC
        S1_ERCC --> S1_QC
        S1_QC --> S1_Kallisto
        S1_QC --> S1_Host
        S1_Host --> S1_Human
        S1_Human --> S1_Dedup
        S1_Dedup --> S1_Subsample
    end
    
    %% Stage 2: Non-Host Alignment
    subgraph Stage2["Stage 2: Non-Host Alignment"]
        direction TB
        S2_NT["NT Alignment<br/>(minimap2)"]
        S2_NR["NR Alignment<br/>(DIAMOND blastx)"]
        S2_NT_Process["Process NT Hits<br/>(filter, dedupe, count)"]
        S2_NR_Process["Process NR Hits<br/>(filter, dedupe, count)"]
        S2_Combine["Combine Taxon Counts<br/>(NT + NR)"]
        S2_Annotate["Annotate Reads<br/>(with taxonomy)"]
        
        S2_NT --> S2_NT_Process
        S2_NR --> S2_NR_Process
        S2_NT_Process --> S2_Combine
        S2_NR_Process --> S2_Combine
        S2_Combine --> S2_Annotate
    end
    
    %% Stage 3: Postprocess
    subgraph Stage3["Stage 3: Postprocess"]
        direction TB
        S3_Assembly["Assembly<br/>(SPAdes)"]
        S3_Coverage["Coverage Stats"]
        S3_Download["Download References<br/>(Top hits)"]
        S3_Blast_NT["BLAST Contigs NT<br/>(Reassign reads)"]
        S3_Blast_NR["BLAST Contigs NR<br/>(Reassign reads)"]
        S3_Merge["Merge Refined Counts"]
        S3_Refine["Refine Annotations"]
        S3_TaxidFasta["Generate Taxid FASTA"]
        S3_Locator["Generate Taxid Locator<br/>(Sort by taxonomy)"]
        
        S3_Assembly --> S3_Coverage
        S3_Assembly --> S3_Blast_NT
        S3_Assembly --> S3_Blast_NR
        S3_Download --> S3_Blast_NT
        S3_Download --> S3_Blast_NR
        S3_Blast_NT --> S3_Merge
        S3_Blast_NR --> S3_Merge
        S3_Merge --> S3_Refine
        S3_Refine --> S3_TaxidFasta
        S3_TaxidFasta --> S3_Locator
    end
    
    %% Stage 4: Experimental
    subgraph Stage4["Stage 4: Experimental"]
        direction TB
        S4_TaxidFasta["Generate Taxid FASTA<br/>(Alternative method)"]
        S4_Locator["Generate Taxid Locator"]
        S4_Coverage["Coverage Visualization"]
        S4_Fastq["Generate Non-host FASTQ<br/>(With duplicate expansion)"]
        
        S4_TaxidFasta --> S4_Locator
    end
    
    %% Connections between stages
    Input --> Stage1
    S1_Subsample -.->|"Subsampled FASTAs<br/>Duplicate clusters"| Stage2
    
    S2_NT_Process -.->|"Alignments (M8)<br/>Hit summaries<br/>Taxon counts"| Stage3
    S2_NR_Process -.->|"Alignments (M8)<br/>Hit summaries<br/>Taxon counts"| Stage3
    S2_Annotate -.->|"Annotated FASTAs"| Stage3
    
    S3_Locator -.->|"Refined annotations<br/>Coverage data<br/>Contig stats"| Stage4
    
    %% Output boxes
    subgraph Outputs["Key Outputs"]
        direction LR
        Out1["QC Reports<br/>Host metrics"]
        Out2["Taxon counts<br/>Alignments"]
        Out3["Assembled contigs<br/>Refined taxonomy"]
        Out4["Visualization data<br/>Non-host reads"]
    end
    
    Stage1 -.-> Out1
    Stage2 -.-> Out2
    Stage3 -.-> Out3
    Stage4 -.-> Out4
    
    %% Styling
    classDef stage fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef task fill:#fff3e0,stroke:#e65100,stroke-width:1px
    classDef output fill:#f3e5f5,stroke:#4a148c,stroke-width:1px
    
    class Stage1,Stage2,Stage3,Stage4 stage
    class Out1,Out2,Out3,Out4 output
```

## Workflow Overview

The Short-Read MNGS (Metagenomic Next-Generation Sequencing) workflow consists of four sequential stages:

### Stage 1: Host Filter
- **Purpose**: Remove host and human sequences, perform quality control
- **Key operations**: ERCC filtering, quality trimming, host/human alignment filtering, deduplication, subsampling
- **Output**: Clean, non-host FASTA sequences ready for microbial analysis

### Stage 2: Non-Host Alignment
- **Purpose**: Identify microbial sequences through database alignment
- **Key operations**: Nucleotide alignment (NT database), protein alignment (NR database), taxonomic classification
- **Output**: Taxonomic assignments and abundance counts

### Stage 3: Postprocess
- **Purpose**: Refine taxonomic assignments through assembly
- **Key operations**: De novo assembly, contig-based realignment, refined taxonomic assignment
- **Output**: High-confidence taxonomic assignments and assembled contigs

### Stage 4: Experimental
- **Purpose**: Generate additional outputs and visualizations
- **Key operations**: Coverage visualization, non-host FASTQ generation
- **Output**: Visualization data and processed read files

## Key Features

- **Dual alignment strategy**: Both nucleotide (minimap2) and protein (DIAMOND) searches
- **Assembly-based refinement**: Uses SPAdes assembly to improve taxonomic assignments
- **Comprehensive filtering**: ERCC, host, human, quality, and complexity filters
- **Duplicate tracking**: Maintains duplicate cluster information throughout pipeline
- **Flexible output formats**: Supports various downstream analyses

## Usage

This workflow is designed to run locally using the `local_driver.wdl` file, which orchestrates all four stages in sequence. Each stage can also be run independently in the production environment.