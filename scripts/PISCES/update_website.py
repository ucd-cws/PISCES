import json

import jsonapi_client

from PISCES import api

taxonomy = "taxonomy_term/scientific_name"

models_as_jsonschema = {
    taxonomy: {'properties': {
        'name': {'type': 'string'},
        'description': {'type': 'string'},
		'parent': {'relation': 'to-many', 'resource': [taxonomy]}
 	}}
}


class WebUploader(object):
	base_web_url = "https://pisces.sf.ucdavis.edu/jsonapi"
	def __init__(self, username, password):
		self.username = username
		self.password = password

		self.session = jsonapi_client.Session(self.base_web_url,
											  schema=models_as_jsonschema,
											  request_kwargs={"auth": (self.username, self.password)})

	def clear_taxonomy(self):
		taxonomy_tree = self.session.get(taxonomy)
		for item in taxonomy_tree.resources:
			print(item.id)  # printing these seems to be important - it doesn't get the URL right on delete unless we do this first /shrug
			print(item.url)
			item.delete()
			try:
				item.commit()
			except json.decoder.JSONDecodeError:  # sitefarm doesn't return a response and the client doesn't like it, but it deleted
				pass

	def update_taxonomy(self):
		taxonomic_tree = api.listing.get_taxonomic_tree()
		for family in taxonomic_tree:
			print(family)
			family_taxonomy = self._new_taxonomy(family, taxonomic_tree[family]["name"])
			for genus in taxonomic_tree[family]["children"]:
				print("--{}".format(genus))
				subtree = taxonomic_tree[family]["children"][genus]
				genus_taxonomy = self._new_taxonomy(genus, subtree["name"], parent=family_taxonomy)
				for species in subtree["children"]:
					print("  --{}".format(species))
					self._new_taxonomy(species, subtree["children"][species]["name"], parent=genus_taxonomy)


	def _new_taxonomy(self, sci_name, common_name, parent=None):
		new_taxonomy = self.session.create(taxonomy)
		new_taxonomy.name = sci_name
		new_taxonomy.description = common_name

		if parent is not None:  # can't get the client to handle nesting relationships, so wrote my own code to do the submit here, leveraging the client for the request itself
			new_taxonomy.parent.append(parent)
			json = new_taxonomy._commit_data()
			json['data']['relationships'] = {"parent": {"data": [{"type": "taxonomy_term--scientific_name", "id": parent.id}]}}
			self.session.http_request("POST", url="{}/{}".format(self.base_web_url, taxonomy), send_json=json)

			# now we need to get the new taxonomy item back, basically, so we can use it in the next layer - this won't work for items that have the same name and description - should add some other ID?
			new_taxonomy = self.session.get(taxonomy, jsonapi_client.Filter(name=sci_name, description=common_name)).resources[0]
		else:
			new_taxonomy.commit()

		return new_taxonomy



def update_species_list():
	pass


# def update_data


def update(username, password):
	pass