def get_public_user_fields(user):
    """
    Returns only the user fields that are allowed to be publicly displayed
    based on the user's privacy settings.

    Input:
        A User instance (preferably fetched with select_related('userprivacysettings'))

    Output:
        A dictionary ready for template rendering.
    """
    privacy = getattr(user, 'userprivacysettings', None)
    
    # If the privacy record does not exist for any reason (should not happen after the signal fix),
    # keep all fields hidden as a safety measure.
    if privacy is None:
        return {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': None,
            'phone_number': None,
            'location': None,
            'birth_year': None,
            'gender': None,
            'education_background': None,
            'is_open_to_work': user.is_open_to_work,
        }

    return {
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email if privacy.show_email else None,
        'phone_number': user.phone_number if privacy.show_phone else None,
        'location': user.location if privacy.show_location else None,
        'birth_year': user.birth_year if privacy.show_birth_year else None,
        'gender': user.gender if privacy.show_gender else None,
        'education_background': user.education_background if privacy.show_education_background else None,
        'is_open_to_work': user.is_open_to_work,
    }