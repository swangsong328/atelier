#!/usr/bin/env python3
"""
Database query script to demonstrate the stored PDF processing data.
This script shows how to retrieve and analyze the comprehensive data stored in the database.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

# Add the pdf_converter package to the path
sys.path.insert(0, str(Path(__file__).parent))

from pdf_converter.database import DatabaseManager
from pdf_converter.utils import format_file_size, format_duration


class DatabaseAnalyzer:
    """Analyzer for the PDF processing database."""
    
    def __init__(self) -> None:
        """Initialize the database analyzer."""
        self.db_manager = DatabaseManager()
    
    def analyze_database(self) -> None:
        """Perform comprehensive database analysis."""
        print("=== PDF Processing Database Analysis ===")
        print()
        
        # Get basic statistics
        self._show_basic_statistics()
        
        # Show recent jobs
        self._show_recent_jobs()
        
        # Show file processing history
        self._show_file_history()
        
        # Show text extraction analysis
        self._show_text_analysis()
        
        # Show table extraction analysis
        self._show_table_analysis()
        
        # Show metadata analysis
        self._show_metadata_analysis()
        
        # Show duplicate files
        self._show_duplicate_files()
    
    def _show_basic_statistics(self) -> None:
        """Show basic processing statistics."""
        print("📊 BASIC STATISTICS")
        print("-" * 40)
        
        try:
            stats = self.db_manager.get_job_statistics()
            
            print(f"Total processing jobs: {stats['total_jobs']}")
            print(f"Completed jobs: {stats['completed_jobs']}")
            print(f"Failed jobs: {stats['failed_jobs']}")
            print(f"Success rate: {stats['success_rate']:.1f}%")
            print(f"Total files processed: {stats['total_files_processed']}")
            print(f"Total text blocks: {stats['total_text_blocks']:,}")
            print(f"Total tables: {stats['total_tables']:,}")
            
        except Exception as e:
            print(f"Error retrieving statistics: {e}")
        
        print()
    
    def _show_recent_jobs(self) -> None:
        """Show recent processing jobs."""
        print("📋 RECENT PROCESSING JOBS")
        print("-" * 40)
        
        try:
            recent_jobs = self.db_manager.get_recent_jobs(10)
            
            if not recent_jobs:
                print("No jobs found in database.")
                return
            
            for job in recent_jobs:
                status_icon = "✅" if job.status == "completed" else "❌" if job.status == "failed" else "🔄"
                print(f"{status_icon} {job.job_id}")
                print(f"   File: {job.input_file_name}")
                print(f"   Size: {format_file_size(job.input_file_size)}")
                print(f"   Status: {job.status}")
                print(f"   Created: {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Pages: {job.pages_processed}, Tables: {job.tables_extracted}, Text: {job.text_blocks_extracted}")
                if job.processing_time:
                    print(f"   Time: {format_duration(job.processing_time)}")
                print()
            
        except Exception as e:
            print(f"Error retrieving recent jobs: {e}")
    
    def _show_file_history(self) -> None:
        """Show file processing history."""
        print("📁 FILE PROCESSING HISTORY")
        print("-" * 40)
        
        try:
            with self.db_manager.get_session() as session:
                # Get all processed files
                from pdf_converter.database.models import ProcessingJobDB
                
                files = session.query(ProcessingJobDB).order_by(
                    ProcessingJobDB.created_at.desc()
                ).all()
                
                if not files:
                    print("No files processed yet.")
                    return
                
                # Group by file name
                file_groups = {}
                for job in files:
                    file_name = job.input_file_name
                    if file_name not in file_groups:
                        file_groups[file_name] = []
                    file_groups[file_name].append(job)
                
                for file_name, jobs in file_groups.items():
                    print(f"📄 {file_name}")
                    print(f"   Processed {len(jobs)} times")
                    print(f"   First: {jobs[-1].created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   Last: {jobs[0].created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   Size: {format_file_size(jobs[0].input_file_size)}")
                    
                    # Show success rate
                    completed = sum(1 for job in jobs if job.status == "completed")
                    success_rate = (completed / len(jobs)) * 100
                    print(f"   Success rate: {success_rate:.1f}%")
                    print()
            
        except Exception as e:
            print(f"Error retrieving file history: {e}")
    
    def _show_text_analysis(self) -> None:
        """Show text extraction analysis."""
        print("📝 TEXT EXTRACTION ANALYSIS")
        print("-" * 40)
        
        try:
            with self.db_manager.get_session() as session:
                from pdf_converter.database.models import ExtractedTextDB
                
                # Get text statistics
                total_texts = session.query(ExtractedTextDB).count()
                if total_texts == 0:
                    print("No text data found.")
                    return
                
                # Get text with most words
                longest_text = session.query(ExtractedTextDB).order_by(
                    ExtractedTextDB.word_count.desc()
                ).first()
                
                # Get text with most characters
                largest_text = session.query(ExtractedTextDB).order_by(
                    ExtractedTextDB.text_length.desc()
                ).first()
                
                # Get average statistics
                avg_word_count = session.query(ExtractedTextDB.word_count).all()
                avg_word_count = sum(wc[0] for wc in avg_word_count) / len(avg_word_count)
                
                avg_text_length = session.query(ExtractedTextDB.text_length).all()
                avg_text_length = sum(tl[0] for tl in avg_text_length) / len(avg_text_length)
                
                print(f"Total text blocks: {total_texts:,}")
                print(f"Average word count: {avg_word_count:.0f}")
                print(f"Average text length: {avg_text_length:.0f} characters")
                
                if longest_text:
                    print(f"Longest text: {longest_text.word_count:,} words")
                    print(f"   From job: {longest_text.job.job_id}")
                    print(f"   Page: {longest_text.page_number}")
                
                if largest_text:
                    print(f"Largest text: {largest_text.text_length:,} characters")
                    print(f"   From job: {largest_text.job.job_id}")
                    print(f"   Page: {largest_text.page_number}")
                
                # Show content type analysis
                texts_with_numbers = session.query(ExtractedTextDB).filter_by(has_numbers=True).count()
                texts_with_emails = session.query(ExtractedTextDB).filter_by(has_emails=True).count()
                texts_with_urls = session.query(ExtractedTextDB).filter_by(has_urls=True).count()
                texts_with_phones = session.query(ExtractedTextDB).filter_by(has_phone_numbers=True).count()
                
                print(f"\nContent Analysis:")
                print(f"   Contains numbers: {texts_with_numbers:,} ({texts_with_numbers/total_texts*100:.1f}%)")
                print(f"   Contains emails: {texts_with_emails:,} ({texts_with_emails/total_texts*100:.1f}%)")
                print(f"   Contains URLs: {texts_with_urls:,} ({texts_with_urls/total_texts*100:.1f}%)")
                print(f"   Contains phone numbers: {texts_with_phones:,} ({texts_with_phones/total_texts*100:.1f}%)")
            
        except Exception as e:
            print(f"Error analyzing text data: {e}")
        
        print()
    
    def _show_table_analysis(self) -> None:
        """Show table extraction analysis."""
        print("📋 TABLE EXTRACTION ANALYSIS")
        print("-" * 40)
        
        try:
            with self.db_manager.get_session() as session:
                from pdf_converter.database.models import ExtractedTableDB
                
                # Get table statistics
                total_tables = session.query(ExtractedTableDB).count()
                if total_tables == 0:
                    print("No table data found.")
                    return
                
                # Get largest table
                largest_table = session.query(ExtractedTableDB).order_by(
                    ExtractedTableDB.total_cells.desc()
                ).first()
                
                # Get average statistics
                avg_rows = session.query(ExtractedTableDB.rows).all()
                avg_rows = sum(r[0] for r in avg_rows) / len(avg_rows)
                
                avg_cols = session.query(ExtractedTableDB.columns).all()
                avg_cols = sum(c[0] for c in avg_cols) / len(avg_cols)
                
                print(f"Total tables: {total_tables:,}")
                print(f"Average size: {avg_rows:.1f} rows × {avg_cols:.1f} columns")
                
                if largest_table:
                    print(f"Largest table: {largest_table.rows} rows × {largest_table.columns} columns")
                    print(f"   Total cells: {largest_table.total_cells:,}")
                    print(f"   From job: {largest_table.job.job_id}")
                    print(f"   Page: {largest_table.page_number}")
                
                # Show table types
                table_types = session.query(ExtractedTableDB.table_type).all()
                type_counts = {}
                for tt in table_types:
                    type_counts[tt[0]] = type_counts.get(tt[0], 0) + 1
                
                print(f"\nTable Types:")
                for table_type, count in type_counts.items():
                    print(f"   {table_type}: {count:,} ({count/total_tables*100:.1f}%)")
                
                # Show data type analysis
                tables_with_numeric = session.query(ExtractedTableDB).filter_by(has_numeric_data=True).count()
                tables_with_dates = session.query(ExtractedTableDB).filter_by(has_date_data=True).count()
                tables_with_currency = session.query(ExtractedTableDB).filter_by(has_currency_data=True).count()
                
                print(f"\nData Type Analysis:")
                print(f"   Contains numeric data: {tables_with_numeric:,} ({tables_with_numeric/total_tables*100:.1f}%)")
                print(f"   Contains date data: {tables_with_dates:,} ({tables_with_dates/total_tables*100:.1f}%)")
                print(f"   Contains currency data: {tables_with_currency:,} ({tables_with_currency/total_tables*100:.1f}%)")
            
        except Exception as e:
            print(f"Error analyzing table data: {e}")
        
        print()
    
    def _show_metadata_analysis(self) -> None:
        """Show PDF metadata analysis."""
        print("📄 PDF METADATA ANALYSIS")
        print("-" * 40)
        
        try:
            with self.db_manager.get_session() as session:
                from pdf_converter.database.models import PDFMetadataDB
                
                # Get metadata statistics
                total_metadata = session.query(PDFMetadataDB).count()
                if total_metadata == 0:
                    print("No metadata found.")
                    return
                
                print(f"Total PDFs with metadata: {total_metadata}")
                
                # Show metadata availability
                with_title = session.query(PDFMetadataDB).filter(PDFMetadataDB.title.isnot(None)).count()
                with_author = session.query(PDFMetadataDB).filter(PDFMetadataDB.author.isnot(None)).count()
                with_subject = session.query(PDFMetadataDB).filter(PDFMetadataDB.subject.isnot(None)).count()
                with_creator = session.query(PDFMetadataDB).filter(PDFMetadataDB.creator.isnot(None)).count()
                
                print(f"\nMetadata Availability:")
                print(f"   Title: {with_title:,} ({with_title/total_metadata*100:.1f}%)")
                print(f"   Author: {with_author:,} ({with_author/total_metadata*100:.1f}%)")
                print(f"   Subject: {with_subject:,} ({with_subject/total_metadata*100:.1f}%)")
                print(f"   Creator: {with_creator:,} ({with_creator/total_metadata*100:.1f}%)")
                
                # Show some sample titles
                titles = session.query(PDFMetadataDB.title).filter(
                    PDFMetadataDB.title.isnot(None)
                ).limit(5).all()
                
                if titles:
                    print(f"\nSample Titles:")
                    for title in titles:
                        if title[0]:
                            print(f"   - {title[0]}")
            
        except Exception as e:
            print(f"Error analyzing metadata: {e}")
        
        print()
    
    def _show_duplicate_files(self) -> None:
        """Show duplicate file processing."""
        print("🔄 DUPLICATE FILE ANALYSIS")
        print("-" * 40)
        
        try:
            duplicates = self.db_manager.get_duplicate_files()
            
            if not duplicates:
                print("No duplicate files found.")
                return
            
            print(f"Found {len(duplicates)} files processed multiple times:")
            
            for dup in duplicates:
                print(f"📄 {dup.file_name}")
                print(f"   Processed {dup.processing_count} times")
                print(f"   First: {dup.first_processed_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Last: {dup.last_processed_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Size: {format_file_size(dup.file_size)}")
                print()
            
        except Exception as e:
            print(f"Error analyzing duplicates: {e}")
    
    def search_content(self, search_term: str) -> None:
        """Search for specific content in the database."""
        print(f"🔍 SEARCHING FOR: '{search_term}'")
        print("-" * 40)
        
        try:
            results = self.db_manager.search_text_content(search_term, limit=10)
            
            if not results:
                print("No matches found.")
                return
            
            print(f"Found {len(results)} matches:")
            
            for result in results:
                print(f"📄 {result.job.input_file_name} (Page {result.page_number})")
                print(f"   Job: {result.job.job_id}")
                print(f"   Words: {result.word_count}, Characters: {result.text_length}")
                
                # Show snippet
                text = result.text_content
                if len(text) > 100:
                    text = text[:100] + "..."
                print(f"   Snippet: {text}")
                print()
            
        except Exception as e:
            print(f"Error searching content: {e}")


def main() -> None:
    """Main function."""
    print("🔍 PDF Processing Database Analyzer")
    print("This script analyzes the comprehensive data stored in the database")
    print()
    
    analyzer = DatabaseAnalyzer()
    
    # Check if database exists
    db_path = Path.home() / ".pdf_converter" / "pdf_converter.db"
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("Please run the test_all_files.py script first to create the database.")
        return
    
    try:
        # Perform comprehensive analysis
        analyzer.analyze_database()
        
        # Interactive search
        print("=" * 60)
        print("🔍 INTERACTIVE SEARCH")
        print("=" * 60)
        
        while True:
            search_term = input("\nEnter search term (or 'quit' to exit): ").strip()
            if search_term.lower() in ['quit', 'exit', 'q']:
                break
            
            if search_term:
                analyzer.search_content(search_term)
        
        print("\n👋 Analysis complete!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Analysis error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 