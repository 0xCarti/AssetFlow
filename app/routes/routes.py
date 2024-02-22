from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app import db
from app.forms import LocationForm, ItemForm, TransferForm
from app.models.models import Location, Item, Transfer, TransferItem

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
    return render_template('items/view_items.html', items=items)


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
    return render_template('items/edit_item.html', form=form,  item=item)


@item.route('/items/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted successfully!')
    return redirect(url_for('item.view_items'))


@transfer.route('/transfers')
@login_required
def view_transfers():
    transfers = Transfer.query.all()
    form = TransferForm()
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
    items = [{"id": item.item_id, "name": item.item.name, "quantity": item.quantity} for item in transfer.transfer_items]
    return render_template('transfers/edit_transfer.html', form=form, transfer=transfer, items=items)



@transfer.route('/transfers/delete/<int:transfer_id>', methods=['POST'])
@login_required
def delete_transfer(transfer_id):
    transfer = Transfer.query.get_or_404(transfer_id)
    db.session.delete(transfer)
    db.session.commit()
    flash('Transfer deleted successfully!', 'success')
    return redirect(url_for('transfer.view_transfers'))


@transfer.route('/transfers/complete/<int:transfer_id>', methods=['POST'])
@login_required
def complete_transfer(transfer_id):
    transfer = Transfer.query.get_or_404(transfer_id)
    transfer.completed = True
    db.session.commit()
    flash('Transfer marked as complete!', 'success')
    return redirect(url_for('transfer.view_transfers'))


@item.route('/items/search', methods=['GET'])
@login_required
def search_items():
    search_term = request.args.get('term', '')
    items = Item.query.filter(Item.name.ilike(f'%{search_term}%')).all()
    items_data = [{'id': item.id, 'name': item.name} for item in items]  # Create a list of dicts
    return jsonify(items_data)