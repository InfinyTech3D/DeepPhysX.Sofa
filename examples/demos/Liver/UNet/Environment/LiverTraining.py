"""
LiverTraining
Simulation of a Liver with FEM computed simulations.
The SOFA simulation contains two models of a Liver:
    * one to apply forces and compute deformations
    * one to apply the network predictions
Training data are produced at each time step :
    * input : applied forces on each surface node
    * output : resulted displacement of each surface node
"""

# Python related imports
import os
import sys
from numpy import ndarray, zeros, double, subtract, reshape
from numpy.linalg import norm

# Session related imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from LiverSofa import LiverSofa


class LiverTraining(LiverSofa):

    def __init__(self,
                 as_tcp_ip_client=True,
                 instance_id=1,
                 instance_nb=1):

        LiverSofa.__init__(self,
                           as_tcp_ip_client=as_tcp_ip_client,
                           instance_id=instance_id,
                           instance_nb=instance_nb)

        self.create_model['nn'] = True

    def init_database(self):
        """
        Define the fields of the training dataset.
        """

        # Define the fields of the Training database
        self.define_training_fields(fields=[('input', ndarray), ('ground_truth', ndarray)])

    def init_visualization(self):
        """
        Define and send the initial visualization data dictionary. Automatically called when creating Environment.
        """

        # Add the mesh model (object will have id = 0)
        self.factory.add_mesh(positions=self.f_visu.position.value.copy(),
                              cells=self.f_visu.triangles.value.copy(),
                              at=self.instance_id,
                              c='green')

    def onAnimateEndEvent(self, event):
        """
        Called within the Sofa pipeline at the end of the time step. Compute training data and apply prediction.
        """

        # Send training data
        self.set_training_data(input=self.compute_input(),
                               ground_truth=self.compute_output())

        # Update visualization
        self.update_visual()

    def compute_input(self):
        """
        Compute force vector for the whole surface.
        """

        # Init encoded forces field to zero
        F = zeros(self.data_size, dtype=double)
        # Encode each force field
        surface_mo = self.f_surface_mo if self.create_model['fem'] else self.n_surface_mo
        for force_field in self.force_field:
            for i in force_field.indices.value:
                # Get the list of nodes composing a cell containing a point from the force field
                p = surface_mo.rest_position.value[i]
                cell = self.regular_grid.cell_index_containing(p)
                # For each node of the cell, encode the force value
                for node in self.regular_grid.node_indices_of(cell):
                    if node < self.nb_nodes_regular_grid and norm(F[node]) == 0.:
                        F[node] = force_field.force.value
        return F

    def compute_output(self):
        """
        Compute displacement vector for the whole surface.
        """

        # Write the position of each point from the sparse grid to the regular grid
        actual_positions_on_regular_grid = zeros(self.data_size, dtype=double)
        actual_positions_on_regular_grid[self.idx_sparse_to_regular] = self.f_sparse_grid_mo.position.array()
        return subtract(actual_positions_on_regular_grid, self.regular_grid_rest_shape)

    def apply_prediction(self, prediction):
        """
        Apply the predicted displacement to the NN model, update visualization data.
        """

        # Reshape to correspond regular grid, transform to sparse grid
        U = reshape(prediction['prediction'], self.data_size)
        U_sparse = U[self.idx_sparse_to_regular]
        self.n_sparse_grid_mo.position.value = self.n_sparse_grid_mo.rest_position.array() + U_sparse

    def update_visual(self):
        """
        Update the visualization data dict.
        """

        # Update mesh position
        self.factory.update_mesh(object_id=0,
                                 positions=self.f_visu.position.value.copy())
        self.update_visualisation()
