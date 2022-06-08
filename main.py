import overpy
import phonenumbers
import requests


def parse_osm_server_response(request_response):
    """
    Parses the response from the OSM's API
    :param request_response: The response from the OSM API
    :return: A list of nodes
    """
    parsed_nodes = []
    list_of_nodes = request_response['elements']
    for response_node in list_of_nodes:
        response_node['tag'] = response_node.pop('tags')
        parsed_nodes.append(response_node)
    return parsed_nodes


def break_down_id_list(node_id_list, maximum_string_length=8000, maximum_number_of_ids=725):
    """
    A helper function to break down the list of IDs into a group of smaller sublist to accommodate OSM's query size limit
    :param maximum_number_of_ids: The maximum number of IDs the API can handle
    :param maximum_string_length: The maximum http string length the API can handle
    :param node_id_list: The complete list containing all the IDs
    :return: A list of lists of IDs
    """
    groups_of_ids = []
    temp_group = []

    for node_id in node_id_list:
        temp_string = ','.join(temp_group)
        if (len(temp_string + ',' + str(node_id)) < maximum_string_length) and (
                len(temp_group) + 1 < maximum_number_of_ids):
            temp_group.append(str(node_id))
        else:
            groups_of_ids.append(temp_group)
            temp_group = [str(node_id)]
    groups_of_ids.append(temp_group)
    return groups_of_ids


def get_node_data_bulk(node_id_list):
    """
    Fetches node data from the OSM database
    :param node_id_list: List of IDs of the nodes to be fetched from the OSM database
    :return: A list of nodes fetched from OSM
    """
    groups_of_node_ids = break_down_id_list(node_id_list)

    fetched_nodes = []

    for group in groups_of_node_ids:
        request_string = 'https://api.openstreetmap.org/api/0.6/nodes?nodes=%s' % ','.join(group)

        request_headers = {'Accept': 'application/json'}
        request = requests.get(request_string, headers=request_headers)
        parsed_nodes = parse_osm_server_response(request.json())
        fetched_nodes.extend(parsed_nodes)

    return fetched_nodes


def get_nodes(overpass_query):
    """
    Returns a list of node IDS queried from Overpass that matches the query and node data fetched from OSM
    :param overpass_query: The overpass query string
    :return: A list of nodes that suffices the query string
    """
    queried_nodes = overpy.Overpass().query(overpass_query).nodes

    node_ids = []

    for node in queried_nodes:
        node_ids.append(node.id)

    if len(node_ids) > 0:
        return get_node_data_bulk(node_ids)
    else:
        return []


def is_valid_phone_number(phone_number, country_code):
    """
    Validates if the given string contains a valid phone number or not
    :param phone_number: The phone number string
    :param country_code: The country code for the localisation
    :return: True if the string contains a valid phone number
    """
    try:
        parsed_phone_number = phonenumbers.parse(phone_number, country_code)
        return phonenumbers.is_valid_number(parsed_phone_number)
    except phonenumbers.NumberParseException:
        pass
    return False


def format_phone_number(phone_number, country_code):
    """
    Formats a valid phone number string according to TUI-T E.123 format pattern
    :param phone_number: The original phone number string with no formatting
    :param country_code: The localisation country code for the phone number
    :return: Formatted phone number string
    """
    parsed_phone_number = phonenumbers.parse(phone_number, country_code)
    phone_number = phonenumbers.format_number(parsed_phone_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    return phone_number


def separate_tag_values(tag_value):
    """
    Separates values of a key into a list
    :param tag_value: The value string of a key
    :return: A list of seperated tag values
    """
    tag_values = tag_value.split(';')
    return tag_values


if __name__ == '__main__':

    tag_key = 'ISO3166-2'
    tag_value = 'NL-GR'

    # Getting nodes from OSM
    overpass_query = 'area["ISO3166-2"="%s-%s"]->.boundary;node(area.boundary)["phone"];out;' % (
    tag_key, tag_value)
    nodes = get_nodes(overpass_query)

    if len(nodes) == 0:
        print("No nodes matched with your query")

    # Processing nodes
    nodes_to_be_updated = []
    test = []

    for counter, node in enumerate(nodes):
        phone_numer_tags = ['phone', 'contact:phone', 'contact:mobile', 'fax', 'contact:fax']
        update_node = False

        # Phone number format correction
        for tag_key in phone_numer_tags:
            if tag_key in node['tag']:
                original_phone_numbers = node['tag'][tag_key]
                original_phone_numbers = separate_tag_values(original_phone_numbers)

                formatted_phone_numbers = []

                for original_phone_number in original_phone_numbers:
                    if is_valid_phone_number(original_phone_number, "NL"):
                        formatted_phone_number = format_phone_number(original_phone_number, 'NL')
                        formatted_phone_numbers.append(formatted_phone_number)
                    else:
                        formatted_phone_numbers.append(original_phone_number)

                if original_phone_numbers != formatted_phone_numbers:
                    print("Node %s Key %s:  %s ==>  %s" % (
                    node['id'], tag_key, ';'.join(original_phone_numbers), '; '.join(formatted_phone_numbers)))
                    node['tag'][tag_key] = '; '.join(formatted_phone_numbers)
                    update_node = True

        # Check if the node needs to be updated or not
        if update_node:
            nodes_to_be_updated.append(node)
