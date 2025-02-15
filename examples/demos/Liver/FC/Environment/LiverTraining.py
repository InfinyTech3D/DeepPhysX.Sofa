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
from numpy import ndarray, zeros, reshape

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
        self.input_size = None
        self.output_size = None

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

    def onSimulationInitDoneEvent(self, event):
        """
        Called within the Sofa pipeline at the end of the scene graph initialisation.
        """

        # Get the data shape
        self.input_size = self.n_surface_mo.position.value.shape
        self.output_size = self.n_sparse_grid_mo.position.value.shape

    def onAnimateEndEvent(self, event):
        """
        Called within the Sofa pipeline at the end of the time step. Compute training data.
        """

        # Send training data
        self.set_training_data(input=self.compute_input(),
                               ground_truth=self.compute_output())

        # Update visualization
        self.update_visual()

    def compute_input(self):
        """
        Compute force field on the surface.
        """

        # Compute applied force on the surface
        F = zeros(self.input_size)
        for cff in self.force_field:
            F[cff.indices.value.copy()] = cff.forces.value.copy()
        return F

    def compute_output(self):
        """
        Compute displacement vector for the whole surface.
        """

        # Compute generated displacement on the grid
        U = self.f_sparse_grid_mo.position.value.copy() - self.f_sparse_grid_mo.rest_position.value.copy()
        return U

    def apply_prediction(self, prediction):
        """
        Apply the predicted displacement to the NN model.
        """

        # Reshape to correspond sparse grid
        U = reshape(prediction['prediction'], self.output_size)
        self.n_sparse_grid_mo.position.value = self.n_sparse_grid_mo.rest_position.array() + U

    def update_visual(self):
        """
        Update the visualization data dict.
        """

        # Update mesh positions
        self.factory.update_mesh(object_id=0,
                                 positions=self.f_visu.position.value.copy())
        self.update_visualisation()
