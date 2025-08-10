import csv
import os
import sys
from fpdf import FPDF
import matplotlib.pyplot as plt
from datetime import datetime

def read_training_data(filename):
    """Read training data from CSV file with enhanced error handling."""
    try:
        # Validate file existence and content
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Error: The file '{filename}' does not exist.")
        
        if os.path.getsize(filename) == 0:
            raise ValueError(f"Error: The file '{filename}' is empty.")
        
        data = []
        with open(filename, 'r') as file:
            reader = csv.DictReader(file)
            
            # Validate CSV structure
            if not reader.fieldnames:
                raise ValueError("Error: CSV file has no headers.")
            
            required_fields = {'Name', 'Module', 'Score', 'Date', 'Completed'}
            if not required_fields.issubset(set(reader.fieldnames)):
                missing = required_fields - set(reader.fieldnames)
                raise ValueError(f"Missing required fields: {', '.join(missing)}")
            
            # Process each row
            for i, row in enumerate(reader, start=1):
                try:
                    # Handle Score field
                    score_str = row['Score'].strip() if row['Score'] else ""
                    row['Score'] = float(score_str) if score_str else None
                    
                    # Handle Completed field - robust to None/empty
                    completed_str = str(row['Completed']).strip().lower() if row['Completed'] is not None else ""
                    row['Completed'] = completed_str == "yes"
                    
                    # Handle Date field
                    date_str = row['Date'].strip() if row['Date'] else ""
                    if date_str:
                        try:
                            row['Date'] = datetime.strptime(date_str, '%Y-%m-%d')
                        except ValueError:
                            row['Date'] = None
                    else:
                        row['Date'] = None
                    
                    data.append(row)
                except (ValueError, TypeError) as e:
                    print(f"Warning: Skipping row {i} due to error: {e}")
                    print(f"Row data: {row}")
        
        if not data:
            raise ValueError("Error: No valid data records found.")
        
        print(f"Successfully read {len(data)} records")
        return data
    
    except Exception as e:
        print(f"Error reading data: {str(e)}")
        sys.exit(1)

def analyze_training_data(data):
    """Analyze training data and compute statistics."""
    try:
        # Get unique modules and participants
        modules = sorted({record['Module'] for record in data})
        participants = sorted({record['Name'] for record in data})
        
        # Module statistics
        module_stats = {}
        for module in modules:
            module_data = [r for r in data if r['Module'] == module]
            completed = [r for r in module_data if r['Completed']]
            scores = [r['Score'] for r in completed if r['Score'] is not None]
            
            module_stats[module] = {
                'completion_rate': len(completed) / len(module_data) * 100 if module_data else 0,
                'average_score': sum(scores) / len(scores) if scores else 0,
                'participants': len({r['Name'] for r in module_data})
            }
        
        # Participant statistics
        participant_stats = {}
        for person in participants:
            person_data = [r for r in data if r['Name'] == person]
            completed = [r for r in person_data if r['Completed']]
            scores = [r['Score'] for r in completed if r['Score'] is not None]
            
            participant_stats[person] = {
                'completion_rate': len(completed) / len(person_data) * 100 if person_data else 0,
                'average_score': sum(scores) / len(scores) if scores else 0,
                'modules_completed': len(completed)
            }
        
        # Find top performers
        qualified_performers = [
            (name, stats) for name, stats in participant_stats.items()
            if stats['completion_rate'] >= 50 and stats['modules_completed'] > 0
        ]
        top_performers = sorted(
            qualified_performers,
            key=lambda x: x[1]['average_score'],
            reverse=True
        )[:3]
        
        # Prepare score trends data
        dated_data = [r for r in data if r['Date'] and r['Score'] is not None]
        if dated_data:
            dated_data.sort(key=lambda x: x['Date'])
            dates = [r['Date'] for r in dated_data]
            scores = [r['Score'] for r in dated_data]
        else:
            dates, scores = None, None
        
        return {
            'module_stats': module_stats,
            'participant_stats': participant_stats,
            'top_performers': top_performers,
            'score_trends': (dates, scores),
            'modules': modules,
            'participants': participants
        }
    
    except Exception as e:
        print(f"Error analyzing data: {str(e)}")
        sys.exit(1)

def generate_progress_chart(analysis, output_path):
    """Generate progress chart and save as image."""
    try:
        if not analysis['score_trends'][0]:
            return None
        
        dates, scores = analysis['score_trends']
        date_strs = [d.strftime('%m-%d') for d in dates]
        
        plt.figure(figsize=(10, 5))
        plt.plot(date_strs, scores, 'o-', color='#1f77b4')
        plt.title('Training Score Trend Over Time')
        plt.xlabel('Date')
        plt.ylabel('Score')
        plt.ylim(0, 100)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        return output_path
    
    except Exception as e:
        print(f"Warning: Could not generate chart - {str(e)}")
        return None

def create_training_report(analysis, chart_path, output_filename):
    """Generate PDF training report."""
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Report title
        pdf.set_font("Arial", 'B', 24)
        pdf.cell(0, 20, "Intern Training Progress Report", 0, 1, 'C')
        pdf.ln(10)
        
        # Program summary
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Program Summary", 0, 1)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 8, f"Total Modules:{len(analysis['modules'])}",0, 1)
        pdf.cell(0, 8, f"Total Participants:{len(analysis['participants'])}", 0, 1)
        pdf.ln(5)
        
        # Module progress table
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Module Progress", 0, 1)
        pdf.ln(5)
        
        # Table headers
        pdf.set_font("Arial", 'B', 12)
        col_widths = [80, 40, 40, 40]
        headers = ["Module", "Completion Rate", "Avg Score", "Participants"]
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
        pdf.ln()
        
        # Table rows
        pdf.set_font("Arial", size=10)
        for module in analysis['modules']:
            stats = analysis['module_stats'][module]
            pdf.cell(col_widths[0], 10, module, 1)
            pdf.cell(col_widths[1], 10, f"{stats['completion_rate']:.1f}%", 1, 0, 'C')
            pdf.cell(col_widths[2], 10, f"{stats['average_score']:.1f}", 1, 0, 'C')
            pdf.cell(col_widths[3], 10, str(stats['participants']), 1, 0, 'C')
            pdf.ln()
        
        # Top performers section
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Top Performers", 0, 1)
        pdf.ln(5)
        
        if analysis['top_performers']:
            # Table headers
            pdf.set_font("Arial", 'B', 12)
            col_widths = [60, 40, 40, 60]
            headers = ["Name", "Avg Score", "Completion", "Modules Completed"]
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
            pdf.ln()
            
            # Table rows
            pdf.set_font("Arial", size=10)
            for name, stats in analysis['top_performers']:
                pdf.cell(col_widths[0], 10, name, 1)
                pdf.cell(col_widths[1], 10, f"{stats['average_score']:.1f}", 1, 0, 'C')
                pdf.cell(col_widths[2], 10, f"{stats['completion_rate']:.1f}%", 1, 0, 'C')
                pdf.cell(col_widths[3], 10, str(stats['modules_completed']), 1, 0, 'C')
                pdf.ln()
        else:
            pdf.cell(0, 10, "No qualified top performers found", 0, 1)
        
        # Progress chart
        if chart_path and os.path.exists(chart_path):
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "Score Trend Over Time", 0, 1)
            pdf.ln(5)
            pdf.image(chart_path, x=10, w=190)
        
        # Save PDF
        pdf.output(output_filename)
        return True
    
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Configuration
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "training_data.csv")
    output_file = os.path.join(script_dir, "training_report.pdf")
    chart_file = os.path.join(script_dir, "progress_chart.png")
    
    print(f"Looking for data file at: {input_file}")
    
    # Read and process data
    training_data = read_training_data(input_file)
    
    # Analyze data
    analysis = analyze_training_data(training_data)
    print("Data analysis completed")
    
    # Generate progress chart
    chart_path = generate_progress_chart(analysis, chart_file)
    if chart_path:
        print(f"Generated progress chart: {chart_path}")
    
    # Generate PDF report
    create_training_report(analysis, chart_path, output_file)
    print(f"Report generated successfully at: {output_file}")
    
    # Clean up chart file
    if chart_path and os.path.exists(chart_path):
        os.remove(chart_path)
        print("Temporary chart file removed")