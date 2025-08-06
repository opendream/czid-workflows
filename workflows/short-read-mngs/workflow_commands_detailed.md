# Short-Read MNGS Workflow - Detailed Command Reference

This document provides a comprehensive overview of all commands executed in each step of the CZ ID short-read metagenomic sequencing pipeline.

## Stage 1: Host Filter

### 1.1 RunValidateInput
**Purpose**: Validate input FASTQ files and truncate if exceeding maximum fragments

**Command**:
```bash
idseq-dag-run-step --workflow-name host_filter \
  --step-module idseq_dag.steps.run_validate_input \
  --step-class PipelineStepRunValidateInput \
  --step-name validate_input_out \
  --input-files '[["input1.fastq", "input2.fastq"]]' \
  --output-files '["validate_input_summary.json", "valid_input1.fastq", "valid_input2.fastq"]' \
  --additional-attributes '{"truncate_fragments_to": MAX_FRAGMENTS, "file_ext": "fastq"}'
```

### 1.2 ERCC Bowtie2 Filter
**Purpose**: Remove ERCC spike-in control sequences

**Commands**:
```bash
# Extract bowtie2 index
tar xf ercc.bowtie2.tar -C /tmp

# Run bowtie2 alignment
bowtie2 -x /tmp/ercc/ercc --very-sensitive-local -p 16 \
  -1 valid_input1.fastq -2 valid_input2.fastq \
  -q -S /tmp/bowtie2_ercc.sam

# Sort SAM file
samtools sort -n -O sam -@ 8 -o /tmp/bowtie2_ercc.sam /tmp/bowtie2_ercc.sam

# Extract unmapped reads (flag 13 for paired-end: read paired + read unmapped + mate unmapped)
samtools fastq -f 13 -1 bowtie2_ercc_filtered1.fastq -2 bowtie2_ercc_filtered2.fastq \
  -0 /dev/null -s /dev/null /tmp/bowtie2_ercc.sam

# Count ERCC hits
samtools view /tmp/bowtie2_ercc.sam | cut -f3 | grep "ERCC-" | sort | uniq -c | \
  awk '{ print $2 "\t" $1}' > bowtie2_ERCC_counts.tsv
```

### 1.3 Fastp QC
**Purpose**: Adapter trimming, quality filtering, and complexity filtering

**Command**:
```bash
fastp -i bowtie2_ercc_filtered1.fastq -I bowtie2_ercc_filtered2.fastq \
  -o fastp1.fastq -O fastp2.fastq \
  -w 16 \
  --dont_eval_duplication \
  --length_required 35 \
  --qualified_quality_phred 17 \
  --unqualified_percent_limit 15 \
  --n_base_limit 15 \
  --sdust_complexity_filter \
  --complexity_threshold 60 \
  --adapter_fasta adapters.fasta \
  --detect_adapter_for_pe
```

### 1.4 Kallisto
**Purpose**: Quantify host transcripts and ERCC

**Commands**:
```bash
# Run kallisto quantification
/kallisto/kallisto quant -i kallisto.idx -o $(pwd) --plaintext \
  --threads=1 --seed=42 \
  fastp1.fastq fastp2.fastq

# Extract ERCC counts
echo -e "target_id\test_counts" > ERCC_counts.tsv
grep ERCC- reads_per_transcript.kallisto.tsv | cut -f1,4 >> ERCC_counts.tsv

# Create transcript-to-gene mapping
# Python script extracts ENSG IDs from transcript IDs
```

### 1.5 Bowtie2 Host Filter
**Purpose**: Remove host genome sequences (first pass)

**Commands**:
```bash
# Extract host genome index
tar xf host.bowtie2.tar -C /tmp

# Align to host genome
bowtie2 -x /tmp/host/host --very-sensitive-local -p 16 \
  -1 fastp1.fastq -2 fastp2.fastq \
  -q -S /tmp/bowtie2.sam

# Create sorted BAM
samtools sort -n -o bowtie2_host.bam -@ 8 -T /tmp /tmp/bowtie2.sam

# Extract unmapped reads
samtools fastq -f 13 -1 bowtie2_host_filtered1.fastq -2 bowtie2_host_filtered2.fastq \
  -0 /dev/null -s /dev/null bowtie2_host.bam
```

### 1.6 HISAT2 Host Filter
**Purpose**: Remove host genome sequences (second pass, splice-aware)

**Commands**:
```bash
# Extract HISAT2 index
tar xf host.hisat2.tar -C /tmp

# Run HISAT2 alignment
/hisat2/hisat2 -x /tmp/host/host -p 10 \
  -1 bowtie2_host_filtered1.fastq -2 bowtie2_host_filtered2.fastq \
  -q -S /tmp/hisat2.sam

# Sort and compress
samtools sort -n -o /tmp/hisat2.bam -@ 8 -l 1 -T /tmp /tmp/hisat2.sam

# Extract unmapped reads
samtools fastq -f 13 -1 hisat2_host_filtered1.fastq -2 hisat2_host_filtered2.fastq \
  -0 /dev/null -s /dev/null /tmp/hisat2.bam
```

### 1.7 Human Filters (Conditional)
**Purpose**: Remove human sequences if host is non-human

Uses same bowtie2 and HISAT2 commands as host filtering but with human genome indices.

### 1.8 Collect Insert Size Metrics
**Purpose**: Calculate insert size distribution for paired-end reads

**Commands**:
```bash
# Sort BAM by coordinate
samtools sort -o bowtie2_coordinate_sorted.bam -@ 8 -T /tmp bowtie2_host.bam

# Collect metrics
picard CollectInsertSizeMetrics \
  I=bowtie2_coordinate_sorted.bam \
  O=picard_insert_metrics.txt \
  H=insert_size_histogram.pdf
```

### 1.9 RunCZIDDedup
**Purpose**: Custom deduplication to identify duplicate read clusters

**Command**:
```bash
idseq-dag-run-step --workflow-name host_filter \
  --step-module idseq_dag.steps.run_czid_dedup \
  --step-class PipelineStepRunCZIDDedup \
  --step-name czid_dedup_out \
  --input-files '[["hisat2_filtered1.fastq", "hisat2_filtered2.fastq"]]' \
  --output-files '["dedup1.fastq","dedup2.fastq", "clusters.csv", "duplicate_cluster_sizes.tsv"]'
```

### 1.10 RunSubsample
**Purpose**: Subsample reads and convert to FASTA format

**Commands**:
```bash
# Convert FASTQ to FASTA
seqtk seq -a dedup1.fastq > /tmp/reads1.fasta
seqtk seq -a dedup2.fastq > /tmp/reads2.fasta

# Create merged FASTA (interleaved with /1 and /2 suffixes)
seqtk mergepe /tmp/reads1.fasta /tmp/reads2.fasta | awk '
  BEGIN { name = ""; }
  /^>.*/ {
    if ($0 != name) {
      name = $0;
      printf("%s/1\n", $0);
    } else {
      printf("%s/2\n", $0);
    }
  }
  ! /^>.*/ { print; }
' > /tmp/reads_merged.fasta

# Run subsampling
idseq-dag-run-step --workflow-name host_filter \
  --step-module idseq_dag.steps.run_subsample \
  --step-class PipelineStepRunSubsample \
  --step-name subsampled_out \
  --input-files '[["reads1.fasta","reads2.fasta","reads_merged.fasta"], ["duplicate_cluster_sizes.tsv"]]' \
  --output-files '["subsampled_1.fa", "subsampled_2.fa", "subsampled_merged.fa"]' \
  --additional-attributes '{"max_fragments": MAX_SUBSAMPLE_FRAGMENTS}'
```

## Stage 2: Non-Host Alignment

### 2.1 RunAlignment_minimap2_out
**Purpose**: Nucleotide alignment against NT database

**Local Mode Commands**:
```bash
# Run minimap2 alignment
minimap2-scatter -cx sr --secondary=yes [minimap2_index] [input_fastas] > gsnap.paf

# Convert PAF to M8 format
paf2blast6.py gsnap.paf gsnap.m8

# Get version
minimap2-scatter --version
```

**Remote Mode**: Uses Python script with `run_alignment()` function

### 2.2 RunAlignment_diamond_out
**Purpose**: Protein alignment against NR database

**Local Mode Commands**:
```bash
# Create diamond database
diamond makedb --in [diamond_index] -d reference

# Run diamond blastx
diamond blastx -d reference -q [input_fastas] -o rapsearch2.m8 --mid-sensitive

# Get version
diamond --version
```

### 2.3 RunCallHitsMinimap2
**Purpose**: Process NT alignments and generate taxon counts

**Command**: Python script that calls:
- `call_hits_m8()` - Process M8 alignments with filters:
  - Min alignment length: 36bp
  - Apply taxon blacklist/whitelist
  - Remove deuterostome hits
- `generate_taxon_count_json_from_m8()` - Generate taxon counts with duplicate cluster recovery

**Outputs**: 
- `gsnap.deduped.m8` - Deduplicated alignments
- `gsnap.hitsummary.tab` - Summary by taxon
- `gsnap_counts_with_dcr.json` - Taxon counts

### 2.4 RunCallHitsDiamond
**Purpose**: Process NR alignments and generate taxon counts

Same as RunCallHitsMinimap2 but for protein alignments with:
- Min alignment length: 0 (no length filter)
- Count type: "NR"

### 2.5 CombineTaxonCounts
**Purpose**: Merge NT and NR taxon counts

**Command**:
```bash
idseq-dag-run-step --workflow-name non_host_alignment \
  --step-module idseq_dag.steps.combine_taxon_counts \
  --step-class PipelineStepCombineTaxonCounts \
  --step-name taxon_count_out \
  --input-files '[[count_files...]]' \
  --output-files '["taxon_counts_with_dcr.json"]'
```

### 2.6 GenerateAnnotatedFasta
**Purpose**: Annotate reads with taxonomy information

**Command**:
```bash
idseq-dag-run-step --workflow-name non_host_alignment \
  --step-module idseq_dag.steps.generate_annotated_fasta \
  --step-class PipelineStepGenerateAnnotatedFasta \
  --step-name annotated_out \
  --input-files '[[fastas], [m8_files], [hitsummary_files], [counts], [duplicate_info]]' \
  --output-files '["annotated_merged.fa", "unidentified.fa"]'
```

## Stage 3: Postprocess

### 3.1 RunAssembly
**Purpose**: De novo assembly of non-host reads

**Commands**:
```bash
# Run SPAdes assembly
idseq-dag-run-step --workflow-name postprocess \
  --step-module idseq_dag.steps.run_assembly \
  --step-class PipelineStepRunAssembly \
  --step-name assembly_out \
  --additional-attributes '{"memory": 200}'

# SPAdes is called internally with options for metagenomic assembly
# Output filtering by min_contig_length (default 100bp)

# Get version
spades.py -v
```

### 3.2 GenerateCoverageStats
**Purpose**: Calculate contig coverage statistics

**Command**:
```bash
idseq-dag-run-step --workflow-name postprocess \
  --step-module idseq_dag.steps.generate_coverage_stats \
  --step-class PipelineStepGenerateCoverageStats \
  --step-name coverage_out \
  --input-files '[assembly_outputs]' \
  --output-files '["contig_coverage.json", "contig_coverage_summary.csv"]'
```

### 3.3 DownloadAccessions (NT & NR)
**Purpose**: Download reference sequences for top hits

**Command**:
```bash
idseq-dag-run-step --workflow-name postprocess \
  --step-module idseq_dag.steps.download_accessions \
  --step-class PipelineStepDownloadAccessions \
  --step-name download_accessions \
  --additional-attributes '{"db_type": "nt"}' # or "nr"
```

### 3.4 BlastContigs (NT & NR)
**Purpose**: BLAST assembled contigs and reassign reads

**Command**:
```bash
idseq-dag-run-step --workflow-name postprocess \
  --step-module idseq_dag.steps.blast_contigs \
  --step-class PipelineStepBlastContigs \
  --step-name refined_[nt/nr]_out \
  --additional-attributes '{
    "db_type": "[nt/nr]",
    "use_taxon_whitelist": true/false,
    "use_deuterostome_filter": true/false
  }'
```

**Internal operations**:
- BLAST contigs against downloaded references
- Reassign reads based on contig alignments
- Apply taxonomic filters
- Generate refined counts

### 3.5 ComputeMergedTaxonCounts
**Purpose**: Merge NT and NR contig-based results

**Command**:
```bash
idseq-dag-run-step --workflow-name postprocess \
  --step-module idseq_dag.steps.compute_merged_taxon_counts \
  --step-class ComputeMergedTaxonCounts \
  --step-name refined_taxon_count_out \
  --additional-files '{
    "lineage_db": "lineage.db",
    "taxon_blacklist": "blacklist.txt",
    "deuterostome_db": "deuterostome.db"
  }'
```

### 3.6 GenerateTaxidFasta
**Purpose**: Create FASTA files with taxid annotations

**Command**:
```bash
idseq-dag-run-step --workflow-name postprocess \
  --step-module idseq_dag.steps.generate_taxid_fasta \
  --step-class PipelineStepGenerateTaxidFasta \
  --step-name refined_taxid_fasta_out \
  --output-files '[
    "refined_taxid_annot_mapped_only.fasta",
    "refined_taxid_annot.fasta"
  ]'
```

### 3.7 GenerateTaxidLocator
**Purpose**: Sort reads by taxonomy and create location indices

**Command**:
```bash
idseq-dag-run-step --workflow-name postprocess \
  --step-module idseq_dag.steps.generate_taxid_locator \
  --step-class PipelineStepGenerateTaxidLocator \
  --step-name refined_taxid_locator_out \
  --output-files '[
    "refined_taxid_annot_sorted_nt.fasta",
    "refined_taxid_locations_nt.json",
    "refined_taxid_annot_sorted_nr.fasta",
    "refined_taxid_locations_nr.json",
    "refined_taxid_annot_sorted_genus_nt.fasta",
    "refined_taxid_locations_genus_nt.json",
    "refined_taxid_annot_sorted_genus_nr.fasta",
    "refined_taxid_locations_genus_nr.json",
    "refined_taxid_annot_sorted_family_nt.fasta",
    "refined_taxid_locations_family_nt.json",
    "refined_taxid_annot_sorted_family_nr.fasta",
    "refined_taxid_locations_family_nr.json",
    "refined_taxid_annot_sorted_genus.fasta",
    "refined_taxid_locations_genus.json"
  ]'
```

## Stage 4: Experimental

### 4.1 GenerateTaxidFasta (Simplified)
**Purpose**: Alternative taxid annotation method

Similar to Stage 3 but outputs only `taxid_annot.fasta`

### 4.2 GenerateTaxidLocator
**Purpose**: Same as Stage 3 - organize reads by taxonomy

### 4.3 GenerateCoverageViz
**Purpose**: Generate coverage visualization data

**Command**:
```bash
idseq-dag-run-step --workflow-name experimental \
  --step-module idseq_dag.steps.generate_coverage_viz \
  --step-class PipelineStepGenerateCoverageViz \
  --step-name coverage_viz_out \
  --additional-files '{"info_db": "nt_info.db"}' \
  --output-files '["coverage_viz_summary.json", individual_coverage_files...]'
```

### 4.4 NonhostFastq
**Purpose**: Generate non-host FASTQ files with duplicate expansion

**Command**:
```bash
idseq-dag-run-step --workflow-name experimental \
  --step-module idseq_dag.steps.nonhost_fastq \
  --step-class PipelineStepNonhostFastq \
  --step-name nonhost_fastq_out \
  --input-files '[original_fastqs, taxid_fasta, duplicate_clusters]' \
  --output-files '["nonhost_R1.fastq", "nonhost_R2.fastq"]' \
  --additional-attributes '{"use_taxon_whitelist": true/false}'
```

## Key Software Versions Used

- **Bowtie2**: For host/human filtering
- **HISAT2**: For splice-aware host filtering
- **fastp**: For quality control and adapter trimming
- **Kallisto**: For transcript quantification
- **minimap2**: For nucleotide alignment
- **DIAMOND**: For protein alignment
- **SPAdes**: For de novo assembly
- **samtools**: For SAM/BAM manipulation
- **seqtk**: For sequence manipulation
- **Picard**: For insert size metrics

## Important Parameters

### Quality Thresholds
- Min read length: 35bp
- Quality score threshold: Q17
- Max unqualified bases: 15%
- Max N bases: 15%
- Complexity threshold: 60 (SDUST)

### Alignment Parameters
- NT min alignment length: 36bp
- NR min alignment length: 0 (no filter)
- Bowtie2 mode: --very-sensitive-local
- minimap2 mode: -cx sr --secondary=yes
- DIAMOND mode: --mid-sensitive

### Assembly Parameters
- Min contig length: 100bp (configurable)
- Memory allocation: 200GB

## Data Flow Summary

1. **Raw FASTQ** → Validation → ERCC filtering → QC filtering
2. **Filtered reads** → Host filtering (2-stage) → Human filtering (conditional)
3. **Non-host reads** → Deduplication → Subsampling → FASTA conversion
4. **FASTA reads** → NT/NR alignment → Taxonomic assignment
5. **Aligned reads** → Assembly → Contig alignment → Refined assignment
6. **Final results** → Taxonomic organization → Visualization data