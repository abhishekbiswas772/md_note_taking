from flask import request, jsonify, Response
from flask_smorest import Blueprint
from service.note_service import NoteTakingService
import tempfile
import os
from models.notes import Notes

note_bp = Blueprint('notes', __name__, url_prefix='/api/notes')
note_service = NoteTakingService()


@note_bp.route('/create', methods=['POST'])
def create_note():
    temp_path = None
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded. Please upload a markdown file."}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if not file.filename.endswith('.md'):
            return jsonify({"error": "Only .md (markdown) files are allowed"}), 400

        fd, temp_path = tempfile.mkstemp(suffix='.md', prefix='note_')
        os.close(fd)

        file.save(temp_path)

        result = note_service.create_note_record(notes_path=temp_path)

        os.remove(temp_path)
        temp_path = None

        return jsonify(result), 201
    except note_service.NoteTakingException as e:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@note_bp.route('/<document_id>/grammar-check', methods=['GET'])
def check_grammar(document_id):
    try:
        result = note_service.checks_for_grammers(document_id=document_id)
        return jsonify(result), 200
    except note_service.NoteTakingException as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@note_bp.route('/<document_id>/render', methods=['GET'])
def render_note(document_id):
    try:
        note = Notes.query.filter_by(id=document_id).first()
        if not note:
            return jsonify({"error": "Note not found"}), 404

        object_path = note.minio_object_path
        if not object_path:
            return jsonify({"error": "MinIO object path not found"}), 404

        response = note_service.minio_client.client.get_object(
            bucket_name=note_service.minio_client.bucket_name,
            object_name=object_path
        )
        md_content = response.read().decode('utf-8')
        response.close()
        response.release_conn()

        import markdown2 as markdown
        html_content = markdown.markdown(md_content, extras=['fenced-code-blocks', 'tables', 'code-friendly'])

        html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Note - {document_id}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            color: #333;
            background: #f9f9f9;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
        }}
        h1 {{
            font-size: 2em;
            border-bottom: 1px solid #eee;
            padding-bottom: 0.3em;
        }}
        code {{
            background: #f6f8fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        pre {{
            background: #f6f8fa;
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
            border: 1px solid #e1e4e8;
        }}
        pre code {{
            background: none;
            padding: 0;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            border: 1px solid #ddd;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f6f8fa;
            font-weight: 600;
        }}
        blockquote {{
            border-left: 4px solid #dfe2e5;
            padding-left: 16px;
            color: #6a737d;
            margin: 0;
        }}
        a {{
            color: #0366d6;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        ul, ol {{
            padding-left: 2em;
        }}
        li {{
            margin: 0.25em 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_content}
    </div>
</body>
</html>"""

        return Response(html_template, mimetype='text/html')

    except Exception as e:
        return jsonify({"error": f"Failed to render note: {str(e)}"}), 500
