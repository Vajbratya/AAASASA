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

    updated_laudo = f"{current_laudo}\n\nSugestão: {suggestion}"

    return jsonify({
        "laudo": updated_laudo,
        "suggestions": generate_suggestions(updated_laudo)
    }), 200

@app.route('/save_laudo', methods=["POST"])
@login_required
def save_laudo():
    data = request.get_json()
    laudo = data.get('laudo', '')

    user = User.query.filter_by(unique_id=session.get("user_id")).first()
    if not user:
        return jsonify({"error": "Usuário não encontrado."}), 404

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

@app.route("/generate_report", methods=["GET", "POST"])
def generate_report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(unique_id=session['user_id']).first()
    templates = Template.query.filter_by(user_id=user.id).all()
    
    if request.method == "POST":
        exame = request.form["exame"]
        achados = request.form["achados"]
        existing_laudo = request.form.get("existing_laudo", "")
        suggestion = request.form.get("suggestion", "")
        
        if existing_laudo and suggestion:
            combined_achados = f"{existing_laudo}\n\nSugestão aplicada: {suggestion}"
        elif existing_laudo:
            combined_achados = f"{existing_laudo}\n\nAchados adicionais: {achados}"
        else:
            combined_achados = achados
        
        laudo = generate_report_wordware(exame, combined_achados)
        if laudo is None:
            laudo = generate_report_anthropic(exame, combined_achados)
        
        if laudo is None:
            flash("Falha ao gerar o laudo. Tente novamente mais tarde.", "error")
            return redirect(url_for('generate_report'))
        
        suggestions = generate_suggestions(laudo)
        
        report = Report(
            exame=exame,
            achados=combined_achados,
            laudo=laudo,
            user_id=user.id
        )
        
        try:
            db.session.add(report)
            db.session.commit()
            user.total_reports += 1
            user.total_time_saved += 0.09
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"Falha ao salvar o laudo: {str(e)}", "error")
            return redirect(url_for('generate_report'))
        
        return render_template('result.html', laudo=laudo, suggestions=suggestions)
    else:
        return render_template("generate_report.html", templates=templates)

@app.route('/meus_laudos')
@login_required
def meus_laudos():
    user = User.query.filter_by(unique_id=session.get('user_id')).first()
    page = request.args.get('page', 1, type=int)
    reports_paginated = Report.query.filter_by(user_id=str(user.id)).order_by(Report.created_at.desc()).paginate(page=page, per_page=25)
    return render_template('meus_laudos.html', reports=reports_paginated.items, next_page=reports_paginated.next_num if reports_paginated.has_next else None, prev_page=reports_paginated.prev_num if reports_paginated.has_prev else None)

@app.route('/template/<int:template_id>', methods=['GET', 'DELETE'])
@login_required
def template(template_id):
    template = Template.query.get_or_404(template_id)
    
    if request.method == 'GET':
        if template.user_id != User.query.filter_by(unique_id=session.get('user_id')).first().id:
            return jsonify({"error": "Unauthorized access"}), 401
        return jsonify({
            'id': template.id,
            'name': template.name,
            'content': template.content
        })
    
    if request.method == 'DELETE':
        if template.user_id != User.query.filter_by(unique_id=session.get('user_id')).first().id:
            return jsonify({"error": "Unauthorized access"}), 401
        try:
            db.session.delete(template)
            db.session.commit()
            return jsonify({"success": "Template deleted"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    with app.app_context():
        upgrade()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
