import os

import socketio
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session
from flask_login import login_required, current_user
from sqlalchemy import func
from werkzeug.utils import secure_filename

from app import db, socketio
from app.forms import LocationForm, ItemForm, TransferForm, ImportItemsForm, DateRangeForm
from app.models import Location, Item, Transfer, TransferItem

# If you're not already using a Blueprint for your main routes, create one.
main = Blueprint('main', __name__)
location = Blueprint('locations', __name__)
item = Blueprint('item', __name__)
transfer = Blueprint('transfer', __name__)


@main.route('/')
@login_required
def home():
    return render_template('home.html', user=current_user)


@location.route('/locations/add', methods=['GET', 'POST'])
@login_required
def add_location():
    form = LocationForm()
    if form.validate_on_submit():
        new_location = Location(name=form.name.data)
        db.session.add(new_location)
        db.session.commit()
        flash('Location added successfully!')
        return redirect(url_for('locations.view_locations'))
    return render_template('locations/add_location.html', form=form)


@location.route('/locations/edit/<int:location_id>', methods=['GET', 'POST'])
@login_required
def edit_location(location_id):
    location = Location.query.get_or_404(location_id)
    form = LocationForm()
    if form.validate_on_submit():
        location.name = form.name.data
        db.session.commit()
        flash('Location updated successfully!')
        return redirect(url_for('locations.view_locations'))
    elif request.method == 'GET':
        form.name.data = location.name
    return render_template('locations/edit_location.html', form=form, location=location)


@location.route('/locations')
@login_required
def view_locations():
    locations = Location.query.all()
    return render_template('locations/view_locations.html', locations=locations)


@location.route('/locations/delete/<int:location_id>', methods=['POST'])
@login_required
def delete_location(location_id):
    location = Location.query.get_or_404(location_id)
    db.session.delete(location)
    db.session.commit()
    flash('Location deleted successfully!')
    return redirect(url_for('locations.view_locations'))


@item.route('/items')
@login_required
def view_items():
    items = Item.query.all()
    form = ItemForm()
    return render_template('items/view_items.html', items=items, form=form)


@item.route('/items/add', methods=['GET', 'POST'])
@login_required
def add_item():
    form = ItemForm()
    if form.validate_on_submit():
        item = Item(name=form.name.data)
        db.session.add(item)
        db.session.commit()
        flash('Item added successfully!')
        return redirect(url_for('item.view_items'))
    return render_template('items/add_item.html', form=form)


@item.route('/items/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    form = ItemForm(obj=item)
    if form.validate_on_submit():
        item.name = form.name.data
        db.session.commit()
        flash('Item updated successfully!')
        return redirect(url_for('item.view_items'))
    return render_template('items/edit_item.html', form=form, item=item)


@item.route('/items/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted successfully!')
    return redirect(url_for('item.view_items'))


@item.route('/items/bulk_delete', methods=['POST'])
@login_required
def bulk_delete_items():
    item_ids = request.form.getlist('item_ids')
    if item_ids:
        Item.query.filter(Item.id.in_(item_ids)).delete(synchronize_session='fetch')
        db.session.commit()
        flash('Selected items have been deleted.', 'success')
    else:
        flash('No items selected.', 'warning')
    return redirect(url_for('item.view_items'))


@transfer.route('/transfers', methods=['GET'])
@login_required
def view_transfers():
    filter_option = request.args.get('filter', 'not_completed')

    form = TransferForm()

    if filter_option == 'completed':
        transfers = Transfer.query.filter_by(completed=True).all()
    elif filter_option == 'not_completed':
        transfers = Transfer.query.filter_by(completed=False).all()
    else:
        transfers = Transfer.query.all()

    return render_template('transfers/view_transfers.html', transfers=transfers, form=form)


@transfer.route('/transfers/add', methods=['GET', 'POST'])
@login_required
def add_transfer():
    form = TransferForm()
    if form.validate_on_submit():
        transfer = Transfer(
            from_location_id=form.from_location_id.data,
            to_location_id=form.to_location_id.data,
            user_id=current_user.id
        )
        db.session.add(transfer)
        # Dynamically determine the number of items added
        items = [key for key in request.form.keys() if key.startswith('items-') and key.endswith('-item')]
        for item_field in items:
            index = item_field.split('-')[1]
            item_id = request.form.get(f'items-{index}-item')
            quantity = request.form.get(f'items-{index}-quantity', type=int)
            if item_id:
                item = Item.query.get(item_id)
                if item and quantity:
                    transfer_item = TransferItem(
                        transfer_id=transfer.id,
                        item_id=item.id,
                        quantity=quantity
                    )
                    db.session.add(transfer_item)
        db.session.commit()

        socketio.emit('new_transfer', {'message': 'New transfer added'})

        flash('Transfer added successfully!', 'success')
        return redirect(url_for('transfer.view_transfers'))

    return render_template('transfers/add_transfer.html', form=form)


@transfer.route('/transfers/edit/<int:transfer_id>', methods=['GET', 'POST'])
@login_required
def edit_transfer(transfer_id):
    transfer = Transfer.query.get_or_404(transfer_id)
    form = TransferForm(obj=transfer)

    if form.validate_on_submit():
        transfer.from_location_id = form.from_location_id.data
        transfer.to_location_id = form.to_location_id.data

        # Clear existing TransferItem entries
        TransferItem.query.filter_by(transfer_id=transfer.id).delete()

        # Dynamically determine the number of items added, similar to the "add" route
        items = [key for key in request.form.keys() if key.startswith('items-') and key.endswith('-item')]
        for item_field in items:
            index = item_field.split('-')[1]
            item_id = request.form.get(f'items-{index}-item')
            quantity = request.form.get(f'items-{index}-quantity', type=int)
            if item_id and quantity:  # Ensure both are provided and valid
                new_transfer_item = TransferItem(
                    transfer_id=transfer.id,
                    item_id=int(item_id),
                    quantity=quantity
                )
                db.session.add(new_transfer_item)

        db.session.commit()
        flash('Transfer updated successfully!', 'success')
        return redirect(url_for('transfer.view_transfers'))
    elif form.errors:
        flash('There was an error submitting the transfer.', 'error')

    # For GET requests or if the form doesn't validate, pass existing items to the template
    items = [{"id": item.item_id, "name": item.item.name, "quantity": item.quantity} for item in
             transfer.transfer_items]
    return render_template('transfers/edit_transfer.html', form=form, transfer=transfer, items=items)


@transfer.route('/transfers/delete/<int:transfer_id>', methods=['POST'])
@login_required
def delete_transfer(transfer_id):
    transfer = Transfer.query.get_or_404(transfer_id)
    db.session.delete(transfer)
    db.session.commit()
    flash('Transfer deleted successfully!', 'success')
    return redirect(url_for('transfer.view_transfers'))


@transfer.route('/transfers/complete/<int:transfer_id>', methods=['GET'])
@login_required
def complete_transfer(transfer_id):
    transfer = Transfer.query.get_or_404(transfer_id)
    transfer.completed = True
    db.session.commit()
    flash('Transfer marked as complete!', 'success')
    return redirect(url_for('transfer.view_transfers'))


@transfer.route('/transfers/uncomplete/<int:transfer_id>', methods=['GET'])
@login_required
def uncomplete_transfer(transfer_id):
    transfer = Transfer.query.get_or_404(transfer_id)
    transfer.completed = False
    db.session.commit()
    flash('Transfer marked as not completed.', 'success')
    return redirect(url_for('transfer.view_transfers'))


@transfer.route('/transfers/view/<int:transfer_id>', methods=['GET'])
@login_required
def view_transfer(transfer_id):
    transfer = Transfer.query.get_or_404(transfer_id)
    transfer_items = TransferItem.query.filter_by(transfer_id=transfer.id).all()
    return render_template('transfers/view_transfer.html', transfer=transfer, transfer_items=transfer_items)


@item.route('/items/search', methods=['GET'])
@login_required
def search_items():
    search_term = request.args.get('term', '')
    items = Item.query.filter(Item.name.ilike(f'%{search_term}%')).all()
    items_data = [{'id': item.id, 'name': item.name} for item in items]  # Create a list of dicts
    return jsonify(items_data)


@item.route('/import_items', methods=['GET', 'POST'])
@login_required
def import_items():
    form = ImportItemsForm()
    if form.validate_on_submit():
        from run import app

        file = form.file.data
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Parse the file
        with open(filepath, 'r') as file:
            for line in file:
                item_name = line.strip()
                if item_name:
                    # Check if item already exists to avoid duplicates
                    existing_item = Item.query.filter_by(name=item_name).first()
                    if not existing_item:
                        # Create a new item instance and add it to the database
                        new_item = Item(name=item_name)
                        db.session.add(new_item)
            db.session.commit()

        flash('Items imported successfully.', 'success')
        return redirect(url_for('item.import_items'))

    return render_template('items/import_items.html', form=form)


@transfer.route('/transfers/generate_report', methods=['GET', 'POST'])
def generate_report():
    form = DateRangeForm()
    if form.validate_on_submit():
        start_datetime = form.start_datetime.data
        end_datetime = form.end_datetime.data

        # Alias for "from" and "to" locations
        from_location = db.aliased(Location)
        to_location = db.aliased(Location)

        aggregated_transfers = db.session.query(
            from_location.name.label('from_location_name'),
            to_location.name.label('to_location_name'),
            Item.name.label('item_name'),
            func.sum(TransferItem.quantity).label('total_quantity')
        ).select_from(Transfer) \
            .join(TransferItem, Transfer.id == TransferItem.transfer_id) \
            .join(Item, TransferItem.item_id == Item.id) \
            .join(from_location, Transfer.from_location_id == from_location.id) \
            .join(to_location, Transfer.to_location_id == to_location.id) \
            .filter(
            Transfer.completed == True,
            Transfer.date_created >= start_datetime,
            Transfer.date_created <= end_datetime
        ) \
            .group_by(
            from_location.name,
            to_location.name,
            Item.name
        ) \
            .order_by(
            from_location.name,
            to_location.name,
            Item.name
        ) \
            .all()

        # Process the results for display or session storage
        session['aggregated_transfers'] = [{
            'from_location_name': result[0],
            'to_location_name': result[1],
            'item_name': result[2],
            'total_quantity': result[3]
        } for result in aggregated_transfers]

        # Store start and end date/time in session for use in the report
        session['report_start_datetime'] = start_datetime.strftime('%Y-%m-%d %H:%M')
        session['report_end_datetime'] = end_datetime.strftime('%Y-%m-%d %H:%M')

        flash('Transfer report generated successfully.', 'success')
        return redirect(url_for('transfer.view_report'))

    return render_template('transfers/generate_report.html', form=form)


@transfer.route('/transfers/report')
def view_report():
    aggregated_transfers = session.get('aggregated_transfers', [])
    return render_template('transfers/view_report.html', aggregated_transfers=aggregated_transfers)
