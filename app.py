        'laudo': report.laudo
    } for report in reports])

@app.route('/apply_suggestion', methods=["POST"])
@login_required
def apply_suggestion():
    data = request.get_json()
    current_laudo = data.get('current_laudo', '')
    suggestion = data.get('suggestion', '')

    if not suggestion:
        return jsonify({"error": "Sugestão inválida."}), 400

    # Implementar lógica para aplicar a sugestão ao laudo
    # Por exemplo, concatenar a sugestão ao laudo existente
    updated_laudo = f"{current_laudo}\n\nSugestão: {suggestion}"

    return jsonify({
        "laudo": updated_laudo,
        "suggestions": []  # Atualizar com novas sugestões, se necessário
    }), 200

@app.route('/save_laudo', methods=["POST"])
@login_required
def save_laudo():
    data = request.get_json()
    laudo = data.get('laudo', '')

    user = User.query.filter_by(unique_id=session.get("user_id")).first()
    if not user:
        return jsonify({"error": "Usuário não encontrado."}), 404

    # Encontrar o último relatório do usuário para atualizar
    report = Report.query.filter_by(user_id=user.id).order_by(Report.created_at.desc()).first()
    if not report:
        return jsonify({"error": "Nenhum relatório encontrado para salvar."}), 404

    report.laudo = laudo

    try:
        db.session.commit()
        return jsonify({"message": "Laudo salvo com sucesso!"}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao salvar laudo: {str(e)}")
        return jsonify({"error": "Falha ao salvar o laudo."}), 500

if __name__ == "__main__":
    with app.app_context():
        upgrade()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
