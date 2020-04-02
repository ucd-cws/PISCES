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

		self.session = jsonapi_client.Session("https://pisces.sf.ucdavis.edu/jsonapi",
											  schema=models_as_jsonschema,
											  request_kwargs={"auth": (self.username, self.password)})

	def update_taxonomy(self):
		taxonomic_tree = api.listing.get_taxonomic_tree()
		for family in taxonomic_tree:
			self._new_taxonomy(family, taxonomic_tree[family]["name"])
			for genus in taxonomic_tree[family]["children"]:
				self._new_taxonomy(genus, taxonomic_tree[genus]["name"], parent=family)
				for species in taxonomic_tree[genus]["children"]:
					self._new_taxonomy(species, taxonomic_tree[species]["name"], parent=genus)


	def _new_taxonomy(self, sci_name, common_name, parent=None):
		new_taxonomy = self.session.create(taxonomy)
		new_taxonomy.name = sci_name
		new_taxonomy.description = "<p>{}</p>".format(common_name)
		if parent is not None:
			new_taxonomy.parent = parent
		new_taxonomy.commit()




def update_species_list():
	pass


# def update_data


def update(username, password):
	pass